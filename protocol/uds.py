"""UDS (ISO 14229) constants shared by the virtual ECU and the tester."""

# Service identifiers
DIAGNOSTIC_SESSION_CONTROL = 0x10
ECU_RESET = 0x11
CLEAR_DIAGNOSTIC_INFORMATION = 0x14
READ_DTC_INFORMATION = 0x19
READ_DATA_BY_IDENTIFIER = 0x22
SECURITY_ACCESS = 0x27
WRITE_DATA_BY_IDENTIFIER = 0x2E
TESTER_PRESENT = 0x3E

SUPPORTED_SERVICES = frozenset(
    {
        DIAGNOSTIC_SESSION_CONTROL,
        ECU_RESET,
        CLEAR_DIAGNOSTIC_INFORMATION,
        READ_DTC_INFORMATION,
        READ_DATA_BY_IDENTIFIER,
        SECURITY_ACCESS,
        WRITE_DATA_BY_IDENTIFIER,
        TESTER_PRESENT,
    }
)

POSITIVE_OFFSET = 0x40
NEGATIVE_RESPONSE = 0x7F

# Sessions
DEFAULT_SESSION = 0x01
EXTENDED_SESSION = 0x03

# Sub-functions
HARD_RESET = 0x01
REQUEST_SEED = 0x01
SEND_KEY = 0x02
REPORT_DTC_BY_STATUS_MASK = 0x02

# Negative response codes
NRC_SERVICE_NOT_SUPPORTED = 0x11
NRC_SUB_FUNCTION_NOT_SUPPORTED = 0x12
NRC_INCORRECT_LENGTH = 0x13
NRC_REQUEST_SEQUENCE_ERROR = 0x24
NRC_REQUEST_OUT_OF_RANGE = 0x31
NRC_SECURITY_ACCESS_DENIED = 0x33
NRC_INVALID_KEY = 0x35
NRC_EXCEEDED_ATTEMPTS = 0x36
NRC_TIME_DELAY_NOT_EXPIRED = 0x37
NRC_NOT_SUPPORTED_IN_SESSION = 0x7F

NRC_NAMES = {
    NRC_SERVICE_NOT_SUPPORTED: "serviceNotSupported",
    NRC_SUB_FUNCTION_NOT_SUPPORTED: "subFunctionNotSupported",
    NRC_INCORRECT_LENGTH: "incorrectMessageLengthOrInvalidFormat",
    NRC_REQUEST_SEQUENCE_ERROR: "requestSequenceError",
    NRC_REQUEST_OUT_OF_RANGE: "requestOutOfRange",
    NRC_SECURITY_ACCESS_DENIED: "securityAccessDenied",
    NRC_INVALID_KEY: "invalidKey",
    NRC_EXCEEDED_ATTEMPTS: "exceededNumberOfAttempts",
    NRC_TIME_DELAY_NOT_EXPIRED: "requiredTimeDelayNotExpired",
    NRC_NOT_SUPPORTED_IN_SESSION: "serviceNotSupportedInActiveSession",
}

DTC_STATUS_CONFIRMED = 0x09  # testFailed | confirmedDTC
DTC_STATUS_AVAILABILITY_MASK = 0xFF
ALL_DTC_GROUP = (0xFF, 0xFF, 0xFF)

# Server timing reported in the DiagnosticSessionControl response.
P2_SERVER_MAX_MS = 50
P2_STAR_SERVER_MAX_MS = 5000

MAX_REQUEST_BYTES = 4095  # ISO-TP limit with a 12-bit length field


def compute_key(seed):
    """Seed-to-key function of the virtual ECU.

    A real ECU uses a secret algorithm. This one is deliberately simple: the
    tests are about the access-control state machine, not about key strength.
    """
    return ((seed ^ 0x5AA5) + 0x1F3B) & 0xFFFF


def session_timing_record():
    """P2 in 1 ms units and P2* in 10 ms units, two bytes each."""
    p2_star = P2_STAR_SERVER_MAX_MS // 10
    return [
        P2_SERVER_MAX_MS >> 8,
        P2_SERVER_MAX_MS & 0xFF,
        p2_star >> 8,
        p2_star & 0xFF,
    ]
