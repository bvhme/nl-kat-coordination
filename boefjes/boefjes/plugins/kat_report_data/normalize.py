import json
from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.reports import ReportData


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    data = json.loads(raw)
    ooi = ReportData(organization=data["organization_code"], report_data=data)
    yield {
        "type": "declaration",
        "ooi": ooi.dict(),
    }
