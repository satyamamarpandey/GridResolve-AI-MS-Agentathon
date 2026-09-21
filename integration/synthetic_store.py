"""Parses synthetic case files into immutable, validated records.

The store refuses anything not labelled SYNTHETIC_ONLY and anything whose
identifiers fall outside the synthetic patterns, so real customer data cannot be
loaded into these mocks by accident.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Iterable, Mapping, Tuple, TypeVar

from . import validation as v
from .contracts import (
    BillingRecord,
    CrmCase,
    CustomerAccount,
    DiagnosticResult,
    MeterEvent,
    MeterEventHistory,
    MeterReading,
    RateComponents,
    UsagePeriod,
)
from .errors import AuthorizationError, ValidationError

R = TypeVar("R")
Raw = Mapping[str, object]
OPEN_STATUS = "OPEN"


@dataclass(frozen=True)
class CaseRecords:
    crm_case: CrmCase
    account: CustomerAccount
    billing_records: Tuple[BillingRecord, ...]
    meter_readings: Tuple[MeterReading, ...]
    meter_events: MeterEventHistory
    diagnostics: Tuple[DiagnosticResult, ...]
    usage_history: Tuple[UsagePeriod, ...]


@dataclass(frozen=True)
class SyntheticStore:
    cases: Mapping[str, CaseRecords]

    def case(self, case_id: str) -> CaseRecords:
        """Records for `case_id`. An unknown case is refused exactly like a forbidden one."""
        records = self.cases.get(case_id)
        if records is None:
            raise AuthorizationError()
        return records


def _field(raw: Raw, key: str) -> object:
    if not isinstance(raw, Mapping) or key not in raw:
        raise ValidationError("%s is missing." % key)
    return raw[key]


def _mapping(raw: Raw, key: str) -> Raw:
    value = _field(raw, key)
    if not isinstance(value, Mapping):
        raise ValidationError("%s must be an object." % key)
    return value


def _rows(raw: Raw, key: str, parse: Callable[[Raw], R]) -> Tuple[R, ...]:
    """Parse an optional list of objects into a tuple. A missing list is empty."""
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(row, Mapping) for row in value):
        raise ValidationError("%s must be a list of objects." % key)
    return tuple(parse(row) for row in value)


def _text(raw: Raw, key: str) -> str:
    value = _field(raw, key)
    if not isinstance(value, str):
        raise ValidationError("%s must be text." % key)
    return value


def _int(raw: Raw, key: str) -> int:
    return v.require_int(key, _field(raw, key))


def _bool(raw: Raw, key: str) -> bool:
    return v.require_bool(key, _field(raw, key))


def _bill(raw: Raw) -> BillingRecord:
    return BillingRecord(_text(raw, "record_id"), _text(raw, "period_start"), _text(raw, "period_end"),
                         _int(raw, "billing_days"), _int(raw, "kwh_billed"),
                         v.to_money("amount_usd", _field(raw, "amount_usd")), _text(raw, "read_type_end"))


def _reading(raw: Raw) -> MeterReading:
    return MeterReading(_text(raw, "record_id"), _text(raw, "read_date"), _text(raw, "read_type"),
                        _int(raw, "register_kwh"))


def _event(raw: Raw) -> MeterEvent:
    return MeterEvent(_text(raw, "record_id"), _text(raw, "event_date"), _text(raw, "type"),
                      str(raw.get("detail", "")))


def _diagnostic(raw: Raw) -> DiagnosticResult:
    return DiagnosticResult(_text(raw, "record_id"), _text(raw, "diagnostic_date"), _text(raw, "type"),
                            _text(raw, "result"), _bool(raw, "tamper_flag"), _bool(raw, "register_fault_flag"))


def _usage(raw: Raw) -> UsagePeriod:
    return UsagePeriod(_text(raw, "period"), _int(raw, "kwh"))


def _account(records: Raw) -> CustomerAccount:
    rate = _mapping(records, "rate_components")
    components = RateComponents(
        v.to_money("energy_charge_usd_per_kwh", _field(rate, "energy_charge_usd_per_kwh")),
        v.to_money("fixed_charge_usd_per_period", _field(rate, "fixed_charge_usd_per_period")))
    return CustomerAccount(_text(records, "account_id"), _text(records, "meter_id"),
                           _text(records, "service_type"), components)


def parse_case(raw: Raw) -> CaseRecords:
    """One case file into CaseRecords. Raises ValidationError on anything unexpected."""
    if _field(raw, "data_classification") != v.SYNTHETIC_CLASSIFICATION:
        raise ValidationError("data_classification must be %s." % v.SYNTHETIC_CLASSIFICATION)
    case_id = v.require_case_id(_field(raw, "case_id"))
    records = _mapping(raw, "synthetic_account_records")
    account = _account(records)
    events = MeterEventHistory(account.meter_id, _rows(records, "meter_events", _event),
                               str(records.get("meter_event_note", "")))
    return CaseRecords(
        crm_case=CrmCase(case_id, account.account_id, _text(raw, "customer_request"), OPEN_STATUS),
        account=account,
        billing_records=_rows(records, "billing_history", _bill),
        meter_readings=_rows(records, "meter_reads", _reading),
        meter_events=events,
        diagnostics=_rows(records, "diagnostic_records", _diagnostic),
        usage_history=_rows(records, "usage_history_kwh", _usage),
    )


def build_store(cases: Iterable[Raw]) -> SyntheticStore:
    """An immutable store of the given synthetic cases. Duplicate ids are refused."""
    parsed: Mapping[str, CaseRecords] = MappingProxyType({})
    for raw in cases:
        records = parse_case(raw)
        if records.crm_case.case_id in parsed:
            raise ValidationError("case_id appears more than once.")
        parsed = MappingProxyType({**parsed, records.crm_case.case_id: records})
    return SyntheticStore(parsed)
