from random import choice

from tgtg_cli.utils.models import Device

# List of random devices
# Format: (brand, model, android version, build number, screen width)
DEVICES = [
    # === Samsung Galaxy S Series ===
    ("samsung", "SM-S928B", "14", "UP1A.231005.007", 1440),  # S24 Ultra
    ("samsung", "SM-S921B", "14", "UP1A.231005.007", 1080),  # S24
    ("samsung", "SM-S926B", "14", "UP1A.231005.007", 1440),  # S24+
    ("samsung", "SM-S918B", "14", "UP1A.231005.007", 1440),  # S23 Ultra
    ("samsung", "SM-S911B", "14", "UP1A.231005.007", 1080),  # S23
    ("samsung", "SM-S916B", "14", "UP1A.231005.007", 1080),  # S23+
    ("samsung", "SM-S908B", "14", "UP1A.231005.007", 1440),  # S22 Ultra
    ("samsung", "SM-S901B", "14", "UP1A.231005.007", 1080),  # S22
    ("samsung", "SM-S906B", "14", "UP1A.231005.007", 1080),  # S22+
    ("samsung", "SM-G998B", "13", "TP1A.220624.014", 1440),  # S21 Ultra
    ("samsung", "SM-G991B", "13", "TP1A.220624.014", 1080),  # S21
    ("samsung", "SM-G996B", "13", "TP1A.220624.014", 1080),  # S21+
    ("samsung", "SM-G781B", "13", "TP1A.220624.014", 1080),  # S20 FE

    # === Samsung Galaxy A Series ===
    ("samsung", "SM-A556B", "14", "UP1A.231005.007", 1080),  # A55
    ("samsung", "SM-A546B", "14", "UP1A.231005.007", 1080),  # A54
    ("samsung", "SM-A536B", "14", "UP1A.231005.007", 1080),  # A53
    ("samsung", "SM-A528B", "13", "TP1A.220624.014", 1080),  # A52s
    ("samsung", "SM-A525F", "13", "TP1A.220624.014", 1080),  # A52
    ("samsung", "SM-A346B", "14", "UP1A.231005.007", 1080),  # A34
    ("samsung", "SM-A336B", "13", "TP1A.220624.014", 1080),  # A33
    ("samsung", "SM-A146B", "14", "UP1A.231005.007", 1080),  # A14
    ("samsung", "SM-A136B", "13", "TP1A.220624.014", 1080),  # A13

    # === Samsung Galaxy Z / Note ===
    # Z Fold5/4: outer cover display width
    ("samsung", "SM-F946B", "14", "UP1A.231005.007", 904),  # Z Fold5
    ("samsung", "SM-F731B", "14", "UP1A.231005.007", 1080),  # Z Flip5
    ("samsung", "SM-F936B", "14", "UP1A.231005.007", 904),  # Z Fold4
    ("samsung", "SM-F721B", "14", "UP1A.231005.007", 1080),  # Z Flip4
    ("samsung", "SM-N986B", "13", "TP1A.220624.014", 1440),  # Note 20 Ultra
    ("samsung", "SM-N981B", "13", "TP1A.220624.014", 1080),  # Note 20

    # === Google Pixel ===
    ("google", "Pixel 8 Pro", "15", "AP3A.241105.008", 1344),
    ("google", "Pixel 8", "15", "AP3A.241105.008", 1080),
    ("google", "Pixel 8a", "14", "AP2A.240805.005", 1080),
    ("google", "Pixel 7 Pro", "14", "AP2A.240805.005", 1440),
    ("google", "Pixel 7", "14", "AP2A.240805.005", 1080),
    ("google", "Pixel 7a", "14", "UQ1A.240205.004", 1080),
    ("google", "Pixel 6 Pro", "14", "UQ1A.240205.004", 1440),
    ("google", "Pixel 6", "14", "UQ1A.240205.004", 1080),
    ("google", "Pixel 6a", "14", "UQ1A.240205.004", 1080),
    ("google", "Pixel 5", "13", "TQ3A.230805.001", 1080),
    ("google", "Pixel 4a", "13", "TQ3A.230805.001", 1080),

    # === Redmi (Budget-/Mid-Range Xiaomi) ===
    ("Redmi", "23049PCD8G", "14", "UKQ1.230804.001", 1080),  # Redmi Note 13
    ("Redmi", "23090RA98G", "14", "UKQ1.230804.001", 1220),  # R. Note 13 Pro
    ("Redmi", "22101316G", "14", "UKQ1.230804.001", 1080),  # Redmi Note 12
    ("Redmi", "2201117TG", "13", "TKQ1.221114.001", 1080),  # Redmi Note 11
    ("Redmi", "22021211RG", "13", "TKQ1.221114.001", 1080),  # R. Note 11 Pro
    ("Redmi", "M2103K19G", "13", "TP1A.220624.014", 1080),  # Redmi Note 10 5G
    ("Redmi", "M2101K7BG", "13", "TP1A.220624.014", 1080),  # Redmi Note 10 Pro

    # === Xiaomi (Flagship) ===
    ("Xiaomi", "2312DRA50G", "14", "UKQ1.230804.001", 1200),  # Xiaomi 14
    ("Xiaomi", "23116PN5BG", "14", "UKQ1.230804.001", 1220),  # Xiaomi 13T Pro
    ("Xiaomi", "23078PND5G", "14", "UKQ1.230804.001", 1220),  # Xiaomi 13T
    ("Xiaomi", "2211133G", "14", "UKQ1.230804.001", 1080),  # Xiaomi 13
    ("Xiaomi", "2201123G", "13", "TKQ1.221114.001", 1080),  # Xiaomi 12
    ("Xiaomi", "M2012K11AG", "13", "TKQ1.221114.001", 1440),  # Xiaomi Mi 11

    # === POCO ===
    ("POCO", "23013RK75G", "13", "TKQ1.221114.001", 1080),  # POCO X5 Pro
    ("POCO", "22111317PG", "13", "TKQ1.221114.001", 1080),  # POCO X5
    ("POCO", "22041216G", "13", "TKQ1.221114.001", 1080),  # POCO F4

    # === OnePlus ===
    ("OnePlus", "CPH2581", "14", "UKQ1.230924.001", 1440),  # OnePlus 12
    ("OnePlus", "CPH2449", "14", "UKQ1.230924.001", 1440),  # OnePlus 11
    ("OnePlus", "LE2123", "14", "UKQ1.230924.001", 1440),  # OnePlus 10 Pro
    ("OnePlus", "CPH2447", "14", "UKQ1.230924.001", 1240),  # Nord 3
    ("OnePlus", "CPH2399", "13", "TKQ1.221114.001", 1080),  # Nord 2T
    ("OnePlus", "CPH2409", "13", "TKQ1.221114.001", 1080),  # Nord CE 2 Lite
    ("OnePlus", "NE2213", "13", "TKQ1.221114.001", 1080),  # Nord 2T

    # === OPPO ===
    ("OPPO", "CPH2557", "14", "UKQ1.230924.001", 1264),  # Find X7
    ("OPPO", "CPH2525", "14", "UKQ1.230924.001", 1440),  # Find X6 Pro
    ("OPPO", "CPH2507", "13", "TKQ1.221114.001", 1080),  # Reno 8 Pro
    ("OPPO", "CPH2363", "13", "TKQ1.221114.001", 720),  # A77

    # === Realme ===
    ("realme", "RMX3710", "14", "UKQ1.230924.001", 1240),  # GT Neo 5
    ("realme", "RMX3571", "13", "TKQ1.221114.001", 1440),  # GT 2 Pro
    ("realme", "RMX3501", "13", "TKQ1.221114.001", 1080),  # 9 Pro+
    ("realme", "RMX3393", "13", "TKQ1.221114.001", 1080),  # 9i

    # === Motorola ===
    ("motorola", "motorola edge 50 pro", "14", "UTAS34.82-12", 1220),
    ("motorola", "motorola edge 40", "14", "U1TAS34.59-100-4", 1080),
    ("motorola", "motorola edge 30", "13", "T1TA33.87-4", 1080),
    ("motorola", "moto g84 5G", "14", "U1UDS34.26-80-3", 1080),
    ("motorola", "moto g73 5G", "14", "U2UD34.33-66-3", 1080),
    ("motorola", "moto g53 5G", "13", "T2TBS33.77-127-5", 720),
    ("motorola", "moto g32", "13", "T1SAS33.1-61-6-2", 1080),

    # === Nothing ===
    ("Nothing", "A142", "14", "UKQ1.231004.002", 1080),  # Phone (2)
    ("Nothing", "A063", "13", "TKQ1.221114.001", 1080),  # Phone (1)
    ("Nothing", "A065", "14", "UKQ1.231004.002", 1084),  # Phone (2a)

    # === Honor ===
    ("HONOR", "ANY-LX1", "13", "HONORANY-LX1", 1312),  # Magic5 Pro
    ("HONOR", "VNE-LX1", "13", "HONORVNE-LX1", 1200),  # 90
    ("HONOR", "RMO-NX1", "13", "HONORRMO-NX1", 1080),  # Magic6 Lite

    # === Sony ===
    ("Sony", "XQ-DQ54", "14", "64.2.A.2.136", 1644),  # Xperia 1 V
    ("Sony", "XQ-CT54", "13", "63.0.A.5.15", 1644),  # Xperia 1 IV
    ("Sony", "XQ-BC52", "13", "61.2.A.3.145", 1080),  # Xperia 5 III

    # === ASUS ===
    ("asus", "ASUS_AI2401", "14", "UKQ1.230917.001", 1080),  # ROG Phone 8
    ("asus", "ASUS_AI2201", "13", "TKQ1.221013.002", 1080),  # ROG Phone 7

    # === Vivo ===
    ("vivo", "V2312", "14", "UKQ1.230924.001", 1260),  # X100
    ("vivo", "V2242", "13", "TKQ1.221114.001", 1080),  # X90

    # === TCL ===
    ("TCL", "T610K", "13", "TKQ1.221114.001", 720),  # 40 SE
    ("TCL", "T766H", "13", "TKQ1.221114.001", 1080),  # 30 5G
]

# Mapping of Android versions to system versions
API_LEVEL = {
    "13": "33",
    "14": "34",
    "15": "35"
}


def get_random_device() -> Device:
    """
    Retrieves a random Android device. The device information contains the
    brand, model, android version, system version, build number and the
    native portrait screen width in pixels.

    Returns:
        Device: Randomly selected Android device.
    """
    brand, model, android_version, build_number, screen_width = (
        choice(DEVICES)
    )
    system_version = API_LEVEL[android_version]
    return Device(
        brand=brand,
        model=model,
        android_version=android_version,
        system_version=system_version,
        build_number=build_number,
        screen_width=screen_width,
    )
