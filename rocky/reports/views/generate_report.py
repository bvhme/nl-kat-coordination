from collections.abc import Sequence
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_weasyprint import WeasyTemplateResponseMixin
from tools.view_helpers import url_with_querystring

from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException
from reports.report_types.definitions import Report
from reports.report_types.helpers import (
    get_ooi_types_with_report,
    get_plugins_for_report_ids,
    get_report_types_for_oois,
)
from reports.views.base import REPORTS_PRE_SELECTION, BaseReportView, ReportBreadcrumbs, get_selection
from rocky.views.ooi_view import BaseOOIListView


class BreadcrumbsGenerateReportView(ReportBreadcrumbs):
    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)
        breadcrumbs += [
            {
                "url": reverse("generate_report_landing", kwargs=kwargs) + selection,
                "text": _("Generate report"),
            },
            {
                "url": reverse("generate_report_select_oois", kwargs=kwargs) + selection,
                "text": _("Select Objects"),
            },
            {
                "url": reverse("generate_report_select_report_types", kwargs=kwargs) + selection,
                "text": _("Select report types"),
            },
            {
                "url": reverse("generate_report_setup_scan", kwargs=kwargs) + selection,
                "text": _("Setup scan"),
            },
            {
                "url": reverse("generate_report_view", kwargs=kwargs) + selection,
                "text": _("View report"),
            },
        ]
        return breadcrumbs


class LandingGenerateReportView(BreadcrumbsGenerateReportView, BaseReportView):
    """
    Landing page to start the 'Generate Report' flow.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(
            reverse("generate_report_select_oois", kwargs=self.get_kwargs())
            + get_selection(request, REPORTS_PRE_SELECTION)
        )


class OOISelectionGenerateReportView(BreadcrumbsGenerateReportView, BaseReportView, BaseOOIListView):
    """
    Select objects for the 'Generate Report' flow.
    """

    template_name = "generate_report/select_oois.html"
    current_step = 3
    ooi_types = get_ooi_types_with_report()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["channel"] = "generate_report"
        context.update(self.get_ooi_filter_forms(self.ooi_types))
        return context


class ReportTypesSelectionGenerateReportView(BreadcrumbsGenerateReportView, BaseReportView, TemplateView):
    """
    Shows all possible report types from a list of OOIs.
    Chooses report types for the 'Generate Report' flow.
    """

    template_name = "generate_report/select_report_types.html"
    current_step = 4

    def get(self, request, *args, **kwargs):
        if not self.selected_oois:
            error_message = _("Select at least one OOI to proceed.")
            messages.add_message(self.request, messages.ERROR, error_message)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["oois"] = self.get_oois()
        context["available_report_types"] = self.get_report_types_for_generate_report(
            get_report_types_for_oois(self.selected_oois)
        )
        return context


class SetupScanGenerateReportView(BreadcrumbsGenerateReportView, BaseReportView, TemplateView):
    """
    Show required and optional plugins to start scans to generate OOIs to include in report.
    """

    template_name = "generate_report/setup_scan.html"
    current_step = 5

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.selected_report_types:
            error_message = _("Select at least one report type to proceed.")
            messages.add_message(self.request, messages.ERROR, error_message)

        if self.all_plugins_enabled["required"] and self.all_plugins_enabled["optional"]:
            return redirect(reverse("generate_report_view", kwargs=kwargs) + get_selection(request))

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plugins"], context["all_plugins_enabled"] = self.get_required_optional_plugins(
            get_plugins_for_report_ids(self.selected_report_types)
        )
        return context


class GenerateReportView(BreadcrumbsGenerateReportView, BaseReportView, TemplateView):
    """
    Shows the report generated from OOIS and report types.
    """

    template_name = "generate_report.html"
    current_step = 6
    report_types: Sequence[type[Report]]

    def get(self, request, *args, **kwargs):
        if not self.are_plugins_enabled(self.plugins):
            warning_message = _("This report may not show all the data as some plugins are not enabled.")
            messages.add_message(self.request, messages.WARNING, warning_message)
        return super().get(request, *args, **kwargs)

    def generate_reports_for_oois(self) -> dict[str, dict[str, dict[str, Any]]]:
        error_reports = []
        report_data: dict[str, dict[str, dict[str, Any]]] = {}
        by_type: dict[str, list[str]] = {}

        for ooi in self.selected_oois:
            ooi_type = Reference.from_str(ooi).class_

            if ooi_type not in by_type:
                by_type[ooi_type] = []

            by_type[ooi_type].append(ooi)

        for report_type in self.report_types:
            oois = {
                ooi for ooi_type in report_type.input_ooi_types for ooi in by_type.get(ooi_type.get_object_type(), [])
            }

            try:
                results = report_type(self.octopoes_api_connector).collect_data(oois, self.observed_at)
            except ObjectNotFoundException:
                error_reports.append(report_type.id)
                continue
            except StopIteration:
                error_reports.append(report_type.id)
                continue

            for ooi, data in results.items():
                if ooi not in report_data:
                    report_data[ooi] = {}

                report_data[ooi][report_type.name] = {"data": data, "template": report_type.template_path}

        # If OOI could not be found or the date is incorrect, it will be shown to the user as a message error
        if error_reports:
            report_types = ", ".join(set(error_reports))
            date = self.observed_at.date()
            error_message = _("No data could be found for %(report_types). Object(s) did not exist on %(date)s.") % {
                "report_types": report_types,
                "date": date,
            }
            messages.add_message(self.request, messages.ERROR, error_message)

        return report_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report_data"] = self.generate_reports_for_oois()
        context["report_types"] = [report.class_attributes() for report in self.report_types]
        context["report_download_url"] = url_with_querystring(
            reverse("generate_report_pdf", kwargs={"organization_code": self.organization.code}),
            True,
            **self.request.GET,
        )
        return context


class GenerateReportPDFView(GenerateReportView, WeasyTemplateResponseMixin):
    template_name = "generate_report_pdf.html"

    pdf_filename = "generate_report.pdf"
    pdf_attachment = False
    pdf_options = {
        "pdf_variant": "pdf/ua-1",
    }
