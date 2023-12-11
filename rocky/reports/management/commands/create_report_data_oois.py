import logging
from datetime import datetime, timezone

from django.conf import settings
from django.core.management import BaseCommand
from tools.models import Organization

from octopoes.api.models import Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.reports import ReportData
from reports.report_types.helpers import REPORTS
from rocky.views.mixins import OOIList


class Command(BaseCommand):
    help = "Creates report data OOIs in the target organization."

    def add_arguments(self, parser):
        parser.add_argument("target", type=str, help="The target organization code.")

    def handle(self, *args, **options):
        valid_time = datetime.now(timezone.utc)
        meta_octopoes_api_connector = OctopoesAPIConnector(settings.OCTOPOES_API, options["target"])

        for organization in Organization.objects.exclude(code=options["target"]):
            octopoes_api_connector = OctopoesAPIConnector(settings.OCTOPOES_API, organization.code)

            report_data_dict = {}

            for report_type in REPORTS:
                report = report_type(octopoes_api_connector)
                logging.info("Generating report %s data for organisation %s", report.name, organization)
                report_data_dict[report.id] = {}
                for ooi in OOIList(octopoes_api_connector, report.input_ooi_types, valid_time)[: OOIList.HARD_LIMIT]:
                    logging.debug("Generating data for %s", ooi.primary_key)
                    data = report.generate_data(ooi.primary_key, valid_time=valid_time)
                    report_data_dict[report.id][ooi.primary_key] = data

            report_data_ooi = ReportData(organization=organization.code, report_data=report_data_dict)
            meta_octopoes_api_connector.save_declaration(Declaration(ooi=report_data_ooi, valid_time=valid_time))
