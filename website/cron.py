import datetime
import gzip
import logging
import os
import shutil
import traceback
import time

import fasteners

from django.core import management
from django.conf import settings
from django_cron import CronJobBase, Schedule
from django.db import transaction

from git import Repo, Actor

import scraper.dossiers
import scraper.documents
import scraper.political_parties
import scraper.parliament_members

from document.models import Submitter
from government.models import GovernmentMember
from parliament.models import PartyMember
from parliament.models import ParliamentMember
from parliament.models import PoliticalParty
from person.models import Person


import openkamer.besluitenlijst
import openkamer.dossier
import openkamer.kamervraag
import openkamer.parliament

from website import settings

logger = logging.getLogger(__name__)


class LockJob(CronJobBase):
    """
    django-cron does provide a file lock backend,
    but this is not working due to issue https://github.com/Tivix/django-cron/issues/74
    """

    def do(self):
        logger.info('BEGIN')
        lockfilepath = os.path.join(settings.CRON_LOCK_DIR, 'tmp_' + self.code + '_lockfile')
        a_lock = fasteners.InterProcessLock(lockfilepath)
        gotten = a_lock.acquire(timeout=1.0)
        try:
            if gotten:
                self.do_imp()
            else:
                logger.info('Not able to acquire lock, job is already running')
        finally:
            if gotten:
                a_lock.release()
        logger.info('END')

    def do_imp(self):
        raise NotImplementedError


class TestJob(LockJob):
    RUN_EVERY_MINS = 0
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'website.cron.TestJob'

    def do_imp(self):
        logger.info('BEGIN')
        time.sleep(10)
        logger.info('END')


class UpdateParliamentAndGovernment(CronJobBase):
    RUN_AT_TIMES = ['18:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'website.cron.UpdateParliamentAndGovernment'

    def do(self):
        logger.info('BEGIN')
        try:
            openkamer.parliament.create_parliament_and_government()
        except Exception as error:
            logger.exception(error)
            raise
        logger.info('END')


class UpdateSubmitters(CronJobBase):
    RUN_AT_TIMES = ['05:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'website.cron.UpdateSubmitters'

    @transaction.atomic
    def do(self):
        logger.info('BEGIN')
        try:
            submitters = Submitter.objects.all()
            n_total = submitters.count()
            counter = 0
            progress_percent = 0
            for submitter in submitters:
                submitter.update_submitter_party_slug()
                if counter/n_total*100 > (progress_percent+1) :
                    progress_percent = counter/n_total*100
                    logger.info(str(int(progress_percent)) + '%')
                counter += 1
        except Exception as error:
            logger.exception(error)
            raise
        logger.info('END')


class UpdateActiveDossiers(LockJob):
    RUN_AT_TIMES = ['19:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'website.cron.UpdateActiveDossiers'

    def do_imp(self):
        # TODO: also update dossiers that have closed since last update
        logger.info('update active dossiers cronjob')
        failed_dossiers = openkamer.dossier.create_wetsvoorstellen_active()
        if failed_dossiers:
            logger.error('the following dossiers failed: ' + str(failed_dossiers))


class UpdateInactiveDossiers(LockJob):
    RUN_EVERY_MINS = 60*24*3  # 3 days
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'website.cron.UpdateInactiveDossiers'

    def do_imp(self):
        logger.info('update inactive dossiers cronjob')
        failed_dossiers = openkamer.dossier.create_wetsvoorstellen_inactive()
        if failed_dossiers:
            logger.error('the following dossiers failed: ' + str(failed_dossiers))


class UpdateBesluitenLijsten(LockJob):
    RUN_AT_TIMES = ['02:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'website.cron.UpdateBesluitenLijsten'

    def do_imp(self):
        logger.info('update besluitenlijsten')
        openkamer.besluitenlijst.create_besluitenlijsten()


class UpdateKamervragenRecent(LockJob):
    RUN_AT_TIMES = ['02:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'website.cron.UpdateKamervragenRecent'

    def do_imp(self):
        logger.info('update kamervragen and kamerantwoorden')
        years = ['2017', '2016']
        for year in years:
            openkamer.kamervraag.create_kamervragen(year, skip_if_exists=False)
            openkamer.kamervraag.create_antwoorden(year, skip_if_exists=True)
            openkamer.kamervraag.link_kamervragen_and_antwoorden()


class UpdateKamervragenAll(LockJob):
    RUN_EVERY_MINS = 60 * 24 * 7  # 7 days
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'website.cron.UpdateKamervragenAll'

    def do_imp(self):
        logger.info('update kamervragen and kamerantwoorden')
        years = ['2017', '2016', '2015', '2014', '2013', '2012', '2011', '2010']
        for year in years:
            openkamer.kamervraag.create_kamervragen(year, skip_if_exists=False)
            openkamer.kamervraag.create_antwoorden(year, skip_if_exists=True)
            openkamer.kamervraag.link_kamervragen_and_antwoorden()


class CleanUnusedPersons(CronJobBase):
    RUN_AT_TIMES = ['04:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'website.cron.CleanUnusedPersons'

    def do(self):
        logger.info('run unused persons cleanup')
        persons = Person.objects.all()
        persons_to_delete_ids = []
        for person in persons:
            members = PartyMember.objects.filter(person=person)
            if members:
                continue
            members = ParliamentMember.objects.filter(person=person)
            if members:
                continue
            members = GovernmentMember.objects.filter(person=person)
            if members:
                continue
            submitters = Submitter.objects.filter(person=person)
            if submitters:
                continue
            persons_to_delete_ids.append(person.id)
        Person.objects.filter(id__in=persons_to_delete_ids).delete()
        logger.info('deleted persons: ' + str(persons_to_delete_ids))
        logger.info('END')


class BackupDaily(CronJobBase):
    RUN_AT_TIMES = ['18:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'website.cron.BackupDaily'

    def do(self):
        logger.info('run daily backup cronjob')
        management.call_command('dbbackup', '--clean')
        try:
            BackupDaily.create_json_dump()
        except Exception as e:
            logger.exception(e)
            raise

    @staticmethod
    def create_json_dump():
        filepath = os.path.join(settings.DBBACKUP_STORAGE_OPTIONS['location'], 'openkamer-' + str(datetime.date.today()) + '.json')
        filepath_compressed = filepath + '.gz'
        with open(filepath, 'w') as fileout:
            management.call_command(
                'dumpdata',
                '--all',
                '--natural-foreign',
                'person',
                'parliament',
                'government',
                'document',
                'stats',
                'website',
                stdout=fileout
            )
        with open(filepath, 'rb') as f_in:
            with gzip.open(filepath_compressed, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(filepath)
        BackupDaily.remove_old_json_dumps(days_old=30)


    @staticmethod
    def remove_old_json_dumps(days_old):
        for (dirpath, dirnames, filenames) in os.walk(settings.DBBACKUP_STORAGE_OPTIONS['location']):
            for file in filenames:
                if '.json.gz' not in file:
                    continue
                filepath = os.path.join(dirpath, file)
                datetime_created = datetime.datetime.fromtimestamp(os.path.getctime(filepath))
                if datetime_created < datetime.datetime.now() - datetime.timedelta(days=days_old):
                    os.remove(filepath)


class CreateCommitWetsvoorstellenIDs(CronJobBase):
    RUN_AT_TIMES = ['20:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'website.cron.CreateCommitWetsvoorstellenIDs'

    @staticmethod
    def dossier_ids_to_file(dossier_ids, filepath):
        dossier_ids = sorted(dossier_ids)
        with open(filepath, 'w') as fileout:
            for dossier_id in dossier_ids:
                fileout.write(dossier_id + '\n')

    def do(self):
        logger.info('BEGIN')
        try:
            repo = Repo(settings.DATA_REPO_DIR)
            assert not repo.bare
            # origin = repo.create_remote('origin', repo.remotes.origin.url)
            # origin.pull()

            filename_iaan = 'wetsvoorstellen/wetsvoorstellen_dossier_ids_initiatief_aanhangig.txt'
            filepath = os.path.join(settings.DATA_REPO_DIR, filename_iaan)
            dossier_ids_in_ac = scraper.dossiers.get_dossier_ids_wetsvoorstellen_initiatief(filter_active=True)
            self.dossier_ids_to_file(dossier_ids_in_ac, filepath)

            filename_iaf = 'wetsvoorstellen/wetsvoorstellen_dossier_ids_initiatief_afgedaan.txt'
            filepath = os.path.join(settings.DATA_REPO_DIR, filename_iaf)
            dossier_ids_in_in = scraper.dossiers.get_dossier_ids_wetsvoorstellen_initiatief(filter_inactive=True)
            assert len(dossier_ids_in_in) > 68
            self.dossier_ids_to_file(dossier_ids_in_in, filepath)

            filename_raan = 'wetsvoorstellen/wetsvoorstellen_dossier_ids_regering_aanhangig.txt'
            filepath = os.path.join(settings.DATA_REPO_DIR, filename_raan)
            dossier_ids_re_ac = scraper.dossiers.get_dossier_ids_wetsvoorstellen_regering(filter_active=True)
            self.dossier_ids_to_file(dossier_ids_re_ac, filepath)

            filename_raf = 'wetsvoorstellen/wetsvoorstellen_dossier_ids_regering_afgedaan.txt'
            filepath = os.path.join(settings.DATA_REPO_DIR, filename_raf)
            dossier_ids_re_in = scraper.dossiers.get_dossier_ids_wetsvoorstellen_regering(filter_inactive=True)
            assert len(dossier_ids_re_in) > 1266
            self.dossier_ids_to_file(dossier_ids_re_in, filepath)

            number_initiatief, number_regering = scraper.dossiers.get_number_of_wetsvoorstellen()
            total_expected = number_regering + number_initiatief
            total_found = len(dossier_ids_in_ac) + len(dossier_ids_in_in) + len(dossier_ids_re_ac) + len(dossier_ids_re_in)
            logger.info('expected: ' + str(total_expected))
            logger.info('found: ' + str(total_found))
            assert total_expected == total_found

            changed_files = repo.git.diff(name_only=True)
            if not changed_files:
                logger.info('no changes')
                logger.info('END')
                return

            filepath_date = os.path.join(settings.DATA_REPO_DIR, 'wetsvoorstellen/date.txt')
            with open(filepath_date, 'w') as fileout:
                fileout.write(datetime.date.today().strftime('%Y-%m-%d'))

            index = repo.index
            index.add([filename_iaan, filename_iaf, filename_raan, filename_raf, 'wetsvoorstellen/date.txt'])
            author = Actor(settings.GIT_AUTHOR_NAME, settings.GIT_AUTHOR_EMAIL)
            index.commit(
                message='update of wetsvoorstellen dossier ids',
                author=author
            )
            # origin.push()
        except:
            logger.error(traceback.format_exc())
            raise
        logger.info('END')


class CreateCommitPartyCSV(CronJobBase):
    RUN_AT_TIMES = ['19:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'website.cron.CreateCommitPartyCSV'

    def do(self):
        logger.info('BEGIN')
        try:
            repo = Repo(settings.DATA_REPO_DIR)
            assert not repo.bare
            # origin = repo.create_remote('origin', repo.remotes.origin.url)
            # origin.pull()

            parties = scraper.political_parties.search_parties()
            filepath = os.path.join(settings.DATA_REPO_DIR, 'fracties/fracties.csv')
            scraper.political_parties.create_parties_csv(parties, filepath)

            changed_files = repo.git.diff(name_only=True)
            if not changed_files:
                logger.info('no changes')
                logger.info('END')
                return

            filepath_date = os.path.join(settings.DATA_REPO_DIR, 'fracties/date.txt')
            with open(filepath_date, 'w') as fileout:
                fileout.write(datetime.date.today().strftime('%Y-%m-%d'))

            index = repo.index
            index.add(['fracties/fracties.csv', 'fracties/date.txt'])
            author = Actor(settings.GIT_AUTHOR_NAME, settings.GIT_AUTHOR_EMAIL)
            index.commit(
                message='update of tweedekamer.nl fracties',
                author=author
            )
            # origin.push()
        except:
            logger.error(traceback.format_exc())
            raise
        logger.info('END')


class CreateCommitParliamentMembersCSV(CronJobBase):
    RUN_AT_TIMES = ['19:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'website.cron.CreateCommitParliamentMembersCSV'

    def do(self):
        logger.info('BEGIN')
        try:
            repo = Repo(settings.DATA_REPO_DIR)
            assert not repo.bare
            # origin = repo.create_remote('origin', repo.remotes.origin.url)
            # origin.pull()

            parties = scraper.parliament_members.search_members()
            filepath = os.path.join(settings.DATA_REPO_DIR, 'kamerleden/tweedekamerleden.csv')
            scraper.parliament_members.create_members_csv(parties, filepath)

            changed_files = repo.git.diff(name_only=True)
            if not changed_files:
                logger.info('no changes')
                logger.info('END')
                return

            filepath_date = os.path.join(settings.DATA_REPO_DIR, 'kamerleden/date.txt')
            with open(filepath_date, 'w') as fileout:
                fileout.write(datetime.date.today().strftime('%Y-%m-%d'))

            index = repo.index
            index.add(['kamerleden/tweedekamerleden.csv', 'kamerleden/date.txt'])
            author = Actor(settings.GIT_AUTHOR_NAME, settings.GIT_AUTHOR_EMAIL)
            index.commit(
                message='update of tweedekamer.nl kamerleden',
                author=author
            )
            # origin.push()
        except:
            logger.error(traceback.format_exc())
            raise
        logger.info('END')


class UpdateSearchIndex(LockJob):
    RUN_AT_TIMES = ['06:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'website.cron.UpdateSearchIndex'

    def do_imp(self):
        logger.info('BEGIN')
        try:
            management.call_command('update_index', remove=True)        
        except Exception as error:
            logger.exception(error)
            raise
        logger.info('END')

