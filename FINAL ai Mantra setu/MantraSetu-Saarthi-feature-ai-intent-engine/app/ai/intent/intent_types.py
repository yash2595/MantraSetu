from enum import Enum


class IntentType(str, Enum):
    # General
    GREETING = "greeting"
    HELP = "help"
    UNKNOWN = "unknown"

    # Spiritual
    GET_PANCHANG = "get_panchang"
    GET_HOROSCOPE = "get_horoscope"
    GET_MUHURAT = "get_muhurat"

    # Puja
    BOOK_PUJA = "book_puja"
    CANCEL_PUJA = "cancel_puja"
    RESCHEDULE_PUJA = "reschedule_puja"

    # Pandit
    FIND_PANDIT = "find_pandit"
    PANDIT_DETAILS = "pandit_details"

    # Navigation
    GO_HOME = "go_home"
    GO_BACK = "go_back"
    GO_PROFILE = "go_profile"

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"

    # Payments
    PAYMENT = "payment"