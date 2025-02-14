from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSARecord
from octopoes.models.ooi.dns.zone import Hostname, ResolvedHostname


def run(hostname: Hostname, additional_oois: list[DNSARecord | DNSAAAARecord], config: dict[str, str]) -> Iterator[OOI]:
    for record in additional_oois:
        yield ResolvedHostname(
            hostname=hostname.reference,
            address=record.address,
        )
