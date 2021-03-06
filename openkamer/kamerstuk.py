import datetime
import logging
import re

import lxml

from django.db import transaction
from django.urls import resolve, Resolver404
from django.urls import reverse

from person.models import Person
from person.util import parse_name_surname_initials
from person.util import parse_surname_comma_surname_prefix

from government.models import GovernmentMember

from parliament.models import ParliamentMember
from parliament.models import PartyMember

from document.models import Dossier
from document.models import Kamerstuk
from document.models import Submitter


logger = logging.getLogger(__name__)


@transaction.atomic
def create_kamerstuk(document, dossier_id, title, metadata, is_attachement):
    logger.info('BEGIN')
    logger.info('document: ' + str(document))
    title_parts = metadata['title_full'].split(';')
    type_short = ''
    type_long = ''
    if len(title_parts) > 2:
        type_short = title_parts[1].strip()
        type_long = title_parts[2].strip()
    if is_attachement:
        type_short = 'Bijlage'
        type_long = 'Bijlage'
    if type_short == '':
        type_short = document.title_short
    if type_short == 'officiële publicatie':
        type_short = title
    if type_long == '':
        type_long = document.title_full
    original_id = find_original_kamerstuk_id(dossier_id, type_long)
    stuk = Kamerstuk.objects.create(
        document=document,
        id_main=dossier_id,
        id_sub=metadata['id_sub'],
        type_short=type_short,
        type_long=type_long,
        original_id=original_id
    )
    logger.info('kamerstuk created: ' + str(stuk))
    logger.info('END')


def find_original_kamerstuk_id(dossier_id, type_long):
    if 'gewijzigd' not in type_long.lower() and 'nota van wijziging' not in type_long.lower():
        return ''
    result_dossier = re.search(r"t.v.v.\s*(?P<main_id>[0-9]*)", type_long)
    result_document = re.search(r"nr.\s*(?P<sub_id>[0-9]*)", type_long)
    main_id = ''
    sub_id = ''
    if result_dossier and 'main_id' in result_dossier.groupdict():
        main_id = result_dossier.group('main_id')
    if result_document and 'sub_id' in result_document.groupdict():
        sub_id = result_document.group('sub_id')
    if main_id and sub_id:
        return main_id + '-' + sub_id
    elif sub_id:
        return str(dossier_id) + '-' + sub_id
    elif 'voorstel van wet' in type_long.lower() or 'nota van wijziging' in type_long.lower():
        return str(dossier_id) + '-voorstel_van_wet'
    return ''


def update_document_html_links(content_html):
    if not content_html:
        return content_html
    tree = lxml.html.fromstring(content_html)
    a_elements = tree.xpath('//a')
    for element in a_elements:
        if not 'href' in element.attrib:
            continue
        url = element.attrib['href']
        new_url = create_new_url(url)
        element.attrib['href'] = new_url
    return lxml.html.tostring(tree).decode('utf-8')


def create_new_url(url):
    match_kamerstuk = re.match("kst-(\d+)-(\d+)", url)
    match_dossier = re.match("/dossier/(\d+)", url)
    new_url = ''
    if match_kamerstuk:
        dossier_id = match_kamerstuk.group(1)
        sub_id = match_kamerstuk.group(2)
        kamerstukken = Kamerstuk.objects.filter(id_main=dossier_id, id_sub=sub_id)
        if kamerstukken.exists():
            new_url = reverse('kamerstuk', args=(dossier_id, sub_id,))
    elif match_dossier:
        dossier_id = match_dossier.group(1)
        if Dossier.objects.filter(dossier_id=dossier_id).exists():
            new_url = reverse('dossier-timeline', args=(dossier_id,))
    if not new_url:
        try:
            resolve(url)
            openkamer_url = True
        except Resolver404:
            openkamer_url = False
        if openkamer_url or url[0] == '#' or 'http' in url:  # openkamer, anchor or external url
            new_url = url
        else:
            if url[0] != '/':
                url = '/' + url
            new_url = 'https://zoek.officielebekendmakingen.nl' + url
    return new_url


def get_active_persons(date):
    pms = ParliamentMember.active_at_date(date)
    gms = GovernmentMember.active_at_date(date)
    person_ids = []
    for pm in pms:
        person_ids.append(pm.person.id)
    for gm in gms:
        person_ids.append(gm.person.id)
    return Person.objects.filter(id__in=person_ids)


@transaction.atomic
def create_submitter(document, submitter, date):
    # TODO: fix this ugly if else mess
    has_initials = len(submitter.split('.')) > 1
    initials = ''
    if has_initials:
        initials, surname, surname_prefix = parse_name_surname_initials(submitter)
    else:
        surname, surname_prefix = parse_surname_comma_surname_prefix(submitter)
    if initials == 'C.S.':  # this is an abbreviation used in old metadata to indicate 'and usual others'
        initials = ''
    person = Person.find_surname_initials(surname=surname, initials=initials)
    if surname == 'JAN JACOB VAN DIJK':  # 'Jan Jacob van Dijk' and ' Jasper van Dijk' have the same surname and initials, to solve this they have included the forename in the surname
        person = Person.objects.filter(forename='Jan Jacob', surname_prefix='van', surname='Dijk', initials='J.J.')[0]
    if surname == 'JASPER VAN DIJK':
        person = Person.objects.filter(forename='Jasper', surname_prefix='van', surname='Dijk', initials='J.J.')[0]
    if surname == 'JAN DE VRIES':
        person = Person.objects.filter(forename='Jan', surname_prefix='de', surname='Vries', initials='J.M.')[0]
    if not person:
        active_persons = get_active_persons(date)
        persons_similar = active_persons.filter(surname__iexact=surname).exclude(initials='').exclude(
            forename='')
        if persons_similar.count() == 1:
            person = persons_similar[0]
    if not person:
        if surname == '' and initials == '':
            persons = Person.objects.filter(surname='', initials='', forename='')
            if persons:
                person = persons[0]
    if not person:
        persons = Person.objects.filter(surname__iexact=surname, initials__iexact=initials)
        if persons:
            person = persons[0]
    if not person:
        logger.warning('Cannot find person: ' + str(surname) + ' ' + str(initials) + '. Creating new person!')
        person = Person.objects.create(surname=surname, surname_prefix=surname_prefix, initials=initials)
    party_members = PartyMember.get_at_date(person, date)
    party_slug = ''
    if party_members:
        party_slug = party_members[0].party.slug
    return Submitter.objects.create(person=person, document=document, party_slug=party_slug)
