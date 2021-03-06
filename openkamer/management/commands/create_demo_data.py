from django.core.management.base import BaseCommand

import openkamer.parliament
import openkamer.dossier
import openkamer.besluitenlijst


class Command(BaseCommand):

    def handle(self, *args, **options):
        openkamer.parliament.create_parties()
        openkamer.parliament.create_governments()
        openkamer.parliament.create_parliament_members()

        # add a few demo dossiers
        openkamer.dossier.create_or_update_dossier('33885')
        openkamer.dossier.create_or_update_dossier('34344')
        openkamer.dossier.create_or_update_dossier('33506')

        openkamer.besluitenlijst.create_besluitenlijsten(max_results_per_commission=20)
