"""Workflow definitions registry for intent execution planning."""

from typing import Any, Mapping

WORKFLOWS: Mapping[str, list[dict[str, Any]]] = {
    "BOOK_PUJA": [
        {
            "action": "SELECT_TEMPLE",
            "target": "TempleList",
            "parameter": "temple",
            "default": "",
            "requires_user_input": False,
            "voice_prompt": None,
        },
        {
            "action": "SELECT_PUJA",
            "target": "PujaList",
            "parameter": "puja",
            "default": "",
            "requires_user_input": False,
            "voice_prompt": None,
        },
        {
            "action": "SELECT_DATE",
            "target": "DatePicker",
            "parameter": "date",
            "default": "",
            "requires_user_input": False,
            "voice_prompt": None,
        },
        {
            "action": "SELECT_TIME",
            "target": "TimeSlotPicker",
            "parameter": "time",
            "default": "",
            "requires_user_input": False,
            "voice_prompt": None,
        },
        {
            "action": "FILL_DETAILS",
            "target": "DevoteeForm",
            "parameter": None,
            "default": "",
            "requires_user_input": True,
            "voice_prompt": "Please provide devotee details for the puja booking.",
        },
        {
            "action": "WAIT_PAYMENT",
            "target": "PaymentGateway",
            "parameter": None,
            "default": "",
            "requires_user_input": True,
            "voice_prompt": "Please complete the payment to finalize your booking.",
        },
    ],
    "VIEW_PANCHANG": [
        {
            "action": "LOAD_PANCHANG",
            "target": "PanchangView",
            "parameter": "date",
            "default": "today",
            "requires_user_input": False,
            "voice_prompt": None,
        },
    ],
    "FIND_PANDIT": [
        {
            "action": "LOAD_PANDITS",
            "target": "PanditList",
            "parameter": "location",
            "default": "",
            "requires_user_input": False,
            "voice_prompt": None,
        },
    ],
    "BOOK_ASTROLOGY": [
        {
            "action": "CHOOSE_ASTROLOGER",
            "target": "AstrologerList",
            "parameter": "astrologer",
            "default": "",
            "requires_user_input": False,
            "voice_prompt": None,
        },
        {
            "action": "CHOOSE_SLOT",
            "target": "SlotPicker",
            "parameter": "slot",
            "default": "",
            "requires_user_input": False,
            "voice_prompt": None,
        },
        {
            "action": "WAIT_PAYMENT",
            "target": "PaymentGateway",
            "parameter": None,
            "default": "",
            "requires_user_input": True,
            "voice_prompt": "Please complete payment for the astrology consultation.",
        },
    ],
    "HOME": [],
    "PROFILE": [],
}
