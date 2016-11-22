import requests
import logging
from itertools import chain

from django.db import models
from django.utils.text import slugify
from django.utils.functional import cached_property

from person.models import Person

from parliament.models import PoliticalParty
from parliament.models import ParliamentMember

from government.models import GovernmentMember

logger = logging.getLogger(__name__)


class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, default='')

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class CategoryDossier(Category):
    def __str__(self):
        return str(self.name)

    class Meta:
        ordering = ['name']
        verbose_name = 'Category (dossier)'
        verbose_name_plural = 'Categories (dossier)'


class CategoryDocument(Category):
    def __str__(self):
        return 'Document category: ' + str(self.name)

    class Meta:
        ordering = ['name']
        verbose_name = 'Category (document)'
        verbose_name_plural = 'Categories (document)'


class Dossier(models.Model):
    dossier_id = models.CharField(max_length=100, blank=True, unique=True)
    categories = models.ManyToManyField(CategoryDossier, blank=True)
    is_active = models.BooleanField(default=True)
    url = models.URLField(blank=True)
    decision = models.CharField(max_length=200, blank=True)

    AANGENOMEN = 'AAN'
    VERWORPEN = 'VER'
    INGETROKKEN = 'ING'
    AANGEHOUDEN = 'AGH'
    IN_BEHANDELING = 'INB'
    ONBEKEND = 'ONB'

    class Meta:
        ordering = ['-dossier_id']

    def __str__(self):
        return str(self.dossier_id)

    @cached_property
    def documents(self):
        return Document.objects.filter(dossier=self)

    @cached_property
    def kamerstukken(self):
        return Kamerstuk.objects.filter(document__dossier=self)

    @cached_property
    def status(self):
        if self.passed:
            return Dossier.AANGENOMEN
        if self.is_active:
            return Dossier.IN_BEHANDELING
        voting = self.voting
        if voting and voting.result == Voting.VERWORPEN:
            return Dossier.VERWORPEN
        elif self.is_withdrawn:
            return Dossier.INGETROKKEN
        # logger.error('status onbekend')
        return Dossier.ONBEKEND

    @cached_property
    def besluitenlijst_cases(self):
        return BesluitItemCase.objects.filter(related_document_ids__contains=self.dossier_id)

    @cached_property
    def start_date(self):
        documents = Document.objects.filter(dossier=self).order_by('date_published')
        if documents.exists():
            return documents[0].date_published
        return None

    @cached_property
    def voting(self):
        votings = Voting.objects.filter(dossier=self.id, is_dossier_voting=True).exclude(result=Voting.AANGEHOUDEN)
        if votings.exists():
            # if votings.count() > 1:
            #     logger.error('more than one dossier voting found for dossier ' + str(self.dossier_id))
            return votings[0]
        return None

    @cached_property
    def title(self):
        # TODO: improve performance
        kamerstukken = self.kamerstukken.select_related('document')
        titles = {}
        for stuk in kamerstukken:
            title = stuk.document.title()
            if title in titles:
                titles[title] += 1
            else:
                titles[title] = 1
        max_titles = 0
        title = 'undefined'
        for key, value in titles.items():
            if value > max_titles:
                title = key
                max_titles = value
        return title

    @cached_property
    def is_withdrawn(self):
        kamerstukken = self.kamerstukken.order_by('-document__date_published')
        if kamerstukken:
            return 'intrekking' in kamerstukken[0].type_long  # latest kamerstuk
        return False

    @cached_property
    def passed(self):
        if 'aangenomen' in self.decision.lower():
            return True
        voting = self.voting
        if voting and voting.result == Voting.AANGENOMEN:
            return True
        return False

    @staticmethod
    def is_active_id(dossier_id):
        active_dossier_ids = Dossier.get_active_dossier_ids()
        return dossier_id in active_dossier_ids

    @staticmethod
    def get_lines_from_url(url):
        response = requests.get(url)
        return response.content.decode('utf-8').splitlines()

    @classmethod
    def get_active_dossier_ids(cls):
        if hasattr(cls, 'active_dossier_ids'):
            return cls.active_dossier_ids
        lines = Dossier.get_lines_from_url(
            'https://raw.githubusercontent.com/openkamer/ok-tknl-wetsvoorstellen/master/wetsvoorstellen_dossier_ids_initiatief_aanhangig.txt')
        lines += Dossier.get_lines_from_url(
            'https://raw.githubusercontent.com/openkamer/ok-tknl-wetsvoorstellen/master/wetsvoorstellen_dossier_ids_regering_aanhangig.txt')
        cls.active_dossier_ids = []
        for line in lines:
            cls.active_dossier_ids.append(line.strip())
        return cls.active_dossier_ids

    @classmethod
    def get_inactive_dossier_ids(cls):
        if hasattr(cls, 'inactive_dossier_ids'):
            return cls.inactive_dossier_ids
        lines = Dossier.get_lines_from_url(
            'https://raw.githubusercontent.com/openkamer/ok-tknl-wetsvoorstellen/master/wetsvoorstellen_dossier_ids_initiatief_afgedaan.txt')
        lines += Dossier.get_lines_from_url(
            'https://raw.githubusercontent.com/openkamer/ok-tknl-wetsvoorstellen/master/wetsvoorstellen_dossier_ids_regering_afgedaan.txt')
        cls.inactive_dossier_ids = []
        for line in lines:
            cls.inactive_dossier_ids.append(line.strip())
        return cls.inactive_dossier_ids


class Document(models.Model):
    dossier = models.ForeignKey(Dossier, blank=True, null=True)
    document_id = models.CharField(max_length=200, blank=True)
    title_full = models.CharField(max_length=500)
    title_short = models.CharField(max_length=200)
    publication_type = models.CharField(max_length=200, blank=True)
    categories = models.ManyToManyField(CategoryDocument, blank=True)
    publisher = models.CharField(max_length=200, blank=True)
    date_published = models.DateField(blank=True, null=True)
    content_html = models.CharField(max_length=200000, blank=True)

    def submitters(self):
        return Submitter.objects.filter(document=self).exclude(person__surname='')

    def title(self):
        return self.title_full.split(';')[0]

    def document_url(self):
        return 'https://zoek.officielebekendmakingen.nl/' + str(self.document_id) + '.html'

    def __str__(self):
        return self.title_short

    class Meta:
        ordering = ['-date_published']


class Submitter(models.Model):
    person = models.ForeignKey(Person)
    document = models.ForeignKey(Document)

    def __str__(self):
        return self.person.fullname()

    def government_members(self):
        """ :returns the government members of this person at the time the documented was published """
        date = self.document.date_published
        gms = GovernmentMember.objects.filter(person=self.person, start_date__lte=date, end_date__gt=date) | GovernmentMember.objects.filter(person=self.person, start_date__lte=date, end_date=None)
        gms = gms.order_by('-end_date')
        return gms


class Kamerstuk(models.Model):
    document = models.ForeignKey(Document)
    id_main = models.CharField(max_length=40, blank=True)
    id_sub = models.CharField(max_length=40, blank=True)
    type_short = models.CharField(max_length=40, blank=True)
    type_long = models.CharField(max_length=100, blank=True)
    original_id = models.CharField(max_length=40, blank=True)  # format: 33885-22

    MOTIE = 'Motie'
    AMENDEMENT = 'Amendement'
    WETSVOORSTEL = 'Wetsvoorstel'
    VERSLAG = 'Verslag'
    NOTA = 'Nota'
    BRIEF = 'Brief'

    def __str__(self):
        return str(self.id_main) + '-' + str(self.id_sub) + ': ' + str(self.type_long)

    def type(self):
        if 'nota' in self.type_short.lower():
            return Kamerstuk.NOTA
        elif 'motie' in self.type_short.lower():
            return Kamerstuk.MOTIE
        elif 'amendement' in self.type_short.lower():
            return Kamerstuk.AMENDEMENT
        elif self.voorstelwet():
            return Kamerstuk.WETSVOORSTEL
        elif 'verslag' in self.type_short.lower():
            return Kamerstuk.VERSLAG
        elif 'brief' in self.type_short.lower():
            return Kamerstuk.BRIEF
        return None

    def id_full(self):
        return str(self.id_main) + '-' + str(self.id_sub)

    @cached_property
    def voting(self):
        votings = Voting.objects.filter(kamerstuk=self)
        if votings.exists():
            return votings[0]
        return None

    def visible(self):
        if self.type_short == 'Koninklijke boodschap':
            return False
        return True

    def voorstelwet(self):
        if 'voorstel van wet' in self.type_short.lower():
            return True
        return False

    def original(self):
        if not self.original_id:
            return None
        ids = self.original_id.split('-')
        if ids[1] == 'voorstel_van_wet':
            kamerstukken = Kamerstuk.objects.filter(id_main=ids[0]).exclude(id=self.id)
            for stuk in kamerstukken:
                if 'voorstel van wet' in stuk.type_short.lower() and 'gewijzigd' not in stuk.type_short.lower():
                    return stuk
        kamerstukken = Kamerstuk.objects.filter(id_main=ids[0], id_sub=ids[1])
        if kamerstukken.exists():
            return kamerstukken[0]
        return None

    def modifications(self):
        if self.voorstelwet():
            stukken = Kamerstuk.objects.filter(original_id=self.id_main+'-voorstel_van_wet').exclude(id=self.id)
        else:
            stukken = Kamerstuk.objects.filter(original_id=self.id_full())
        return stukken.order_by('document__date_published', 'id_sub')

    class Meta:
        verbose_name_plural = 'Kamerstukken'
        ordering = ['-document__date_published', '-id_sub',]


class Agenda(models.Model):
    document = models.ForeignKey(Document)
    agenda_id = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return str(self.document)


class AgendaItem(models.Model):
    agenda = models.ForeignKey(Agenda)
    dossier = models.ForeignKey(Dossier, null=True)
    item_text = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return str(self.agenda)

    
class Voting(models.Model):
    AANGENOMEN = 'AAN'
    VERWORPEN = 'VER'
    INGETROKKEN = 'ING'
    AANGEHOUDEN = 'AGH'
    ONBEKEND = 'ONB'
    CHOICES = (
        (AANGENOMEN, 'Aangenomen'), (VERWORPEN, 'Verworpen'), (INGETROKKEN, 'Ingetrokken'),
        (AANGEHOUDEN, 'Aangehouden'), (ONBEKEND, 'ONB')
    )
    dossier = models.ForeignKey(Dossier)
    kamerstuk = models.ForeignKey(Kamerstuk, blank=True, null=True)
    is_dossier_voting = models.BooleanField(default=False)
    result = models.CharField(max_length=3, choices=CHOICES)
    date = models.DateField(auto_now=False, blank=True)

    @cached_property
    def votes(self):
        return list(chain(self.votes_party, self.votes_individual))

    @cached_property
    def votes_for(self):
        return list(chain(
            VoteParty.objects.filter(voting=self, decision=Vote.FOR),
            VoteIndividual.objects.filter(voting=self, decision=Vote.FOR)
        ))

    @cached_property
    def votes_against(self):
        return list(chain(
            VoteParty.objects.filter(voting=self, decision=Vote.AGAINST),
            VoteIndividual.objects.filter(voting=self, decision=Vote.AGAINST)
        ))

    @cached_property
    def votes_none(self):
        return list(chain(
            VoteParty.objects.filter(voting=self, decision=Vote.NONE),
            VoteIndividual.objects.filter(voting=self, decision=Vote.NONE)
        ))

    @cached_property
    def votes_party(self):
        return VoteParty.objects.filter(voting=self)

    @cached_property
    def votes_individual(self):
        return VoteIndividual.objects.filter(voting=self)

    def has_result_details(self):
        return len(self.votes) > 0

    def entities_for_string(self):
        entities_str = ''
        for vote in self.votes:
            if vote.decision == Vote.FOR:
                entities_str += vote.get_name() + ', '
        return entities_str

    def entities_against_string(self):
        entities_str = ''
        for vote in self.votes:
            if vote.decision == Vote.AGAINST:
                entities_str += vote.get_name() + ', '
        return entities_str

    def entities_none_string(self):
        entities_str = ''
        for vote in self.votes:
            if vote.decision == Vote.NONE:
                entities_str += vote.get_name() + ', '
        return entities_str

    @cached_property
    def result_percent(self):
        n_votes = 0
        vote_for = 0
        vote_against = 0
        vote_none = 0
        for vote in self.votes:
            n_votes += vote.number_of_seats
            if vote.decision == Vote.FOR:
                vote_for += vote.number_of_seats
            elif vote.decision == Vote.AGAINST:
                vote_against += vote.number_of_seats
            elif vote.decision == Vote.NONE:
                vote_none += vote.number_of_seats
        if n_votes == 0:
            return None
        for_percent = vote_for/n_votes * 100.0
        against_percent = vote_against/n_votes * 100.0
        no_vote_percent = vote_none/n_votes * 100.0
        return {'for': for_percent, 'against': against_percent, 'no_vote': no_vote_percent}

    def __str__(self):
        return 'Dossier: ' + self.dossier.dossier_id + ', result: ' + self.result


class Vote(models.Model):
    FOR = 'FO'
    AGAINST = 'AG'
    NONE = 'NO'
    MISTAKE = 'MI'
    CHOICES = (
        (FOR, 'For'), (AGAINST, 'Against'), (NONE, 'None'), (MISTAKE, 'Mistake')
    )

    voting = models.ForeignKey(Voting)
    number_of_seats = models.IntegerField()
    decision = models.CharField(max_length=2, choices=CHOICES)
    details = models.CharField(max_length=2000, blank=True, null=False, default='')

    def get_name(self):
        raise NotImplementedError

    def __str__(self):
        return str(self.voting) + ' - ' + str(self.decision)


class VoteParty(Vote):
    party = models.ForeignKey(PoliticalParty)

    def get_name(self):
        return self.party.name_short


class VoteIndividual(Vote):
    parliament_member = models.ForeignKey(ParliamentMember, blank=True, null=True)

    def get_name(self):
        return str(self.parliament_member)


class BesluitenLijst(models.Model):
    title = models.CharField(max_length=300)
    commission = models.CharField(max_length=50)
    activity_id = models.CharField(max_length=100)
    date_published = models.DateField()
    url = models.URLField()

    class Meta:
        ordering = ['-date_published']

    def items(self):
        return BesluitItem.objects.filter(besluiten_lijst=self)

    def cases_all(self):
        return BesluitItemCase.objects.filter(besluit_item__in=self.items())

    def related_dossier_ids(self):
        dossier_ids = []
        for case in self.cases_all():
            document_ids = case.related_document_id_list()
            for doc_id in document_ids:
                if doc_id:
                    dossier_ids.append(doc_id.split('-')[0])
        return dossier_ids


class BesluitItem(models.Model):
    title = models.CharField(max_length=300)
    besluiten_lijst = models.ForeignKey(BesluitenLijst)

    def cases(self):
        return BesluitItemCase.objects.filter(besluit_item=self)


class BesluitItemCase(models.Model):
    title = models.CharField(max_length=300)
    besluit_item = models.ForeignKey(BesluitItem)
    decisions = models.CharField(max_length=500)
    notes = models.CharField(max_length=500)
    related_commissions = models.CharField(max_length=500)
    related_document_ids = models.CharField(max_length=300)
    SEP_CHAR = '|'

    def decision_list(self):
        return self.decisions.split(self.SEP_CHAR)

    def note_list(self):
        return self.notes.split(self.SEP_CHAR)

    def related_commission_list(self):
        return self.related_commissions.split(self.SEP_CHAR)

    def related_document_id_list(self):
        return self.related_document_ids.split(self.SEP_CHAR)
