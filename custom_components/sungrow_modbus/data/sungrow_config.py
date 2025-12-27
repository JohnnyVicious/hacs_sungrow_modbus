from typing import List

from custom_components.sungrow_modbus.data.enums import InverterType, InverterFeature


class InverterOptions:
    def __init__(self, pv: bool = True, battery: bool = True, hv_battery: bool = False, v2: bool = True):
        self.pv = pv
        self.battery = battery
        self.hv_battery = hv_battery
        self.v2 = v2


class InverterConfig:
    def __init__(self, model: str, wattage: List[int], phases: int, type: InverterType,
                 options: InverterOptions = None, connection="S2_WL_ST",
                 features=None):
        if options is None:
            options = InverterOptions()
        if features is None:
            features = []
        self.model = model
        self.wattage = wattage
        self.phases = phases
        self.type = type
        self.options = options
        self.connection = connection
        self.features: [InverterFeature] = features
        self.wattage_chosen = max(wattage)

        self._rebuild_features()

    def _rebuild_features(self):
        """Rebuild features list based on current options and connection."""
        self.features = [InverterFeature.BMS]  # Always include BMS

        # Get options - handle both dict and InverterOptions object
        if isinstance(self.options, dict):
            pv = self.options.get("pv", True)
            battery = self.options.get("battery", True)
            hv_battery = self.options.get("hv_battery", False)
            v2 = self.options.get("v2", True)
        else:
            pv = self.options.pv
            battery = self.options.battery
            hv_battery = self.options.hv_battery
            v2 = self.options.v2

        if pv:
            self.features.append(InverterFeature.PV)
        if battery:
            self.features.append(InverterFeature.BATTERY)
        if hv_battery:
            self.features.append(InverterFeature.HV_BATTERY)
        if v2:
            self.features.append(InverterFeature.V2)
        if self.type == InverterType.WAVESHARE or self.connection == "WAVESHARE":
            self.features.append(InverterFeature.TCP)

        # Three-phase detection based on phases count
        if self.phases == 3:
            self.features.append(InverterFeature.THREE_PHASE)

        # MPPT3 detection based on model and wattage
        # T-series hybrids (SH5T-SH25T) with 15kW+ typically have 3 MPPTs
        # Large commercial inverters (25kW+) typically have 3+ MPPTs
        if self._has_mppt3():
            self.features.append(InverterFeature.MPPT3)

    def _has_mppt3(self) -> bool:
        """Determine if this inverter model has a third MPPT."""
        model_upper = self.model.upper()

        # T-series hybrids (SH5T, SH10T, etc.) - larger models have 3 MPPTs
        # Pattern: SHxxT (not SHxxRT which is RT-series with 2 MPPTs)
        if model_upper.startswith("SH") and model_upper.endswith("T") and "RT" not in model_upper:
            # SH15T, SH20T, SH25T have 3 MPPTs
            if self.wattage_chosen >= 15000:
                return True

        # Large commercial string inverters (SG series) with 3+ MPPTs
        # Models like SG30KTL-M, SG40CX, etc.
        if model_upper.startswith("SG"):
            if self.wattage_chosen >= 30000:
                return True

        # Any inverter 25kW+ is likely to have 3 MPPTs
        if self.wattage_chosen >= 25000:
            return True

        return False

    def update_options(self, options: dict, connection: str = None):
        """Update options and rebuild features."""
        self.options = options
        if connection is not None:
            self.connection = connection
        self._rebuild_features()


# Sungrow Inverter Models
# Model naming conventions:
#   SG = String (Grid-tied, non-hybrid)
#   SH = Storage Hybrid
#   RS = Residential Single-phase
#   RT = Residential Three-phase
#   T = Three-phase (larger capacity)
#   -S suffix = Single MPPT variant
#   -ADA suffix = Advanced Diagnostic version with smart meter
#   -L suffix = Lightweight/Low voltage variant
#   -20, -V112, -V122, -V11 = Hardware/firmware variants

SUNGROW_INVERTERS = [
    # ==============================================================================
    # STRING INVERTERS (Non-Hybrid, Grid-tied only)
    # ==============================================================================

    # --- Single-phase String Inverters (SG-RS-S series) - 1 MPPT ---
    InverterConfig(model="SG2.0RS-S", wattage=[2000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG2.5RS-S", wattage=[2500], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG3.0RS-S", wattage=[3000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),

    # --- Single-phase String Inverters (SG-RS series) - 2 MPPT ---
    InverterConfig(model="SG3.0RS", wattage=[3000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG3.6RS", wattage=[3600], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG4.0RS", wattage=[4000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG5.0RS", wattage=[5000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG6.0RS", wattage=[6000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),

    # --- Single-phase String Inverters (SG-RS series) - Higher power, 3+ MPPT ---
    InverterConfig(model="SG8.0RS", wattage=[8000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG9.0RS", wattage=[9000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG10RS", wattage=[10000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),

    # --- Single-phase String Inverters (SG-RS-ADA series) - with smart meter ---
    InverterConfig(model="SG5.0RS-ADA", wattage=[5000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG10RS-ADA", wattage=[10000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG10RS-G3-ADA", wattage=[10000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),

    # --- Single-phase String Inverters (SG-RS-L series) - Low voltage variant ---
    InverterConfig(model="SG8.0RS-L", wattage=[8000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG9.0RS-L", wattage=[9000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG10RS-L", wattage=[10000], phases=1, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),

    # --- Three-phase String Inverters (SG-RT series) ---
    InverterConfig(model="SG5.0RT", wattage=[5000], phases=3, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG6.0RT", wattage=[6000], phases=3, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG7.0RT", wattage=[7000], phases=3, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG8.0RT", wattage=[8000], phases=3, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG10RT", wattage=[10000], phases=3, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG12RT", wattage=[12000], phases=3, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG15RT", wattage=[15000], phases=3, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG17RT", wattage=[17000], phases=3, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),
    InverterConfig(model="SG20RT", wattage=[20000], phases=3, type=InverterType.STRING,
                   options=InverterOptions(battery=False)),

    # ==============================================================================
    # HYBRID INVERTERS (With battery storage support)
    # ==============================================================================

    # --- Single-phase Hybrid - Legacy models (SH series) ---
    InverterConfig(model="SH3K6", wattage=[3600], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="SH4K6", wattage=[4600], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="SH5K-20", wattage=[5000], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="SH5K-V13", wattage=[5000], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="SH3K6-30", wattage=[3600], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="SH4K6-30", wattage=[4600], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="SH5K-30", wattage=[5000], phases=1, type=InverterType.HYBRID),

    # --- Single-phase Hybrid (SH-RS series) - Current generation ---
    InverterConfig(model="SH3.0RS", wattage=[3000], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="SH3.6RS", wattage=[3600], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="SH4.0RS", wattage=[4000], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="SH5.0RS", wattage=[5000], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="SH6.0RS", wattage=[6000], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="SH8.0RS", wattage=[8000], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="SH10RS", wattage=[10000], phases=1, type=InverterType.HYBRID),

    # --- Three-phase Hybrid (SH-RT series) - Base models ---
    InverterConfig(model="SH5.0RT", wattage=[5000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH6.0RT", wattage=[6000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH8.0RT", wattage=[8000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH10RT", wattage=[10000], phases=3, type=InverterType.HYBRID),

    # --- Three-phase Hybrid (SH-RT series) - 20 variants ---
    InverterConfig(model="SH5.0RT-20", wattage=[5000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH6.0RT-20", wattage=[6000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH8.0RT-20", wattage=[8000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH10RT-20", wattage=[10000], phases=3, type=InverterType.HYBRID),

    # --- Three-phase Hybrid (SH-RT series) - V112 variants ---
    InverterConfig(model="SH5.0RT-V112", wattage=[5000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH6.0RT-V112", wattage=[6000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH8.0RT-V112", wattage=[8000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH10RT-V112", wattage=[10000], phases=3, type=InverterType.HYBRID),

    # --- Three-phase Hybrid (SH-RT series) - V122 variants ---
    InverterConfig(model="SH5.0RT-V122", wattage=[5000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH6.0RT-V122", wattage=[6000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH8.0RT-V122", wattage=[8000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH10RT-V122", wattage=[10000], phases=3, type=InverterType.HYBRID),

    # --- Three-phase Hybrid (SH-T series) - Larger capacity residential ---
    InverterConfig(model="SH5T", wattage=[5000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH6T", wattage=[6000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH8T", wattage=[8000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH10T", wattage=[10000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH12T", wattage=[12000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH15T", wattage=[15000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH20T", wattage=[20000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH25T", wattage=[25000], phases=3, type=InverterType.HYBRID),

    # --- Three-phase Hybrid (SH-T series) - V11 variants ---
    InverterConfig(model="SH20T-V11", wattage=[20000], phases=3, type=InverterType.HYBRID),
    InverterConfig(model="SH25T-V11", wattage=[25000], phases=3, type=InverterType.HYBRID),

    # ==============================================================================
    # SPECIAL / OTHER
    # ==============================================================================

    # --- Mobile/Residential (MG series) ---
    InverterConfig(model="MG5RL", wattage=[5000], phases=1, type=InverterType.HYBRID),
    InverterConfig(model="MG6RL", wattage=[6000], phases=1, type=InverterType.HYBRID),

    # --- Waveshare adapter connection ---
    InverterConfig(model="WAVESHARE", wattage=[10000], phases=3, type=InverterType.HYBRID),
]


CONNECTION_METHOD = {
    "S2_WL_ST": "S2_WL_ST",
    "WAVESHARE": "WAVESHARE",
}
