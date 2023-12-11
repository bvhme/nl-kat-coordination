from typing import Dict, Literal

from octopoes.models import OOI, Reference


class ReportData(OOI):
    object_type: Literal["ReportData"] = "ReportData"
    organization: str
    report_data: Dict

    _natural_key_attrs = ["organization"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"Report data of organization {reference.tokenized.organization}"
