
from __future__ import annotations

from pathlib import Path
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =============================================================================
# Physical rationale and source references for the time-series model
# =============================================================================
#
# Purpose of the model
# --------------------
# The model distributes a known annual final or useful energy demand for space
# heating and domestic hot water to hourly time steps. A unique hourly load curve
# cannot be derived from one annual energy total alone. Therefore, the model first
# builds a physically motivated weighting function and then normalizes it exactly
# to the specified annual energy amount.
#
# Core idea for space heating
# ---------------------------
# The hourly space-heating load is derived from a simplified building heat balance:
#
#     q_dot_heat,raw(t)
#       = max(0,
#             H_loss * (T_balance(t) - T_out,eff(t))
#             - Q_dot_solar,usable(t))
#
# where:
#
#     H_loss
#         total heat-loss coefficient from transmission and ventilation [W/K]
#
#     T_balance(t)
#         dynamic balance or heating-limit temperature [°C].
#         It represents, in simplified form, the room-air setpoint, internal gains,
#         system/control effects, and optional night setback.
#
#     T_out,eff(t)
#         thermally smoothed outdoor air temperature [°C].
#         The smoothing represents the delay caused by the building structure.
#
#     Q_dot_solar,usable(t)
#         usable solar gains through window areas [kW].
#         They are estimated from global irradiance, window area, g-value,
#         a simplified orientation factor, and a utilization factor.
#
# The max(0, ...) term represents the heating limit: if the thermally effective
# outdoor air temperature plus solar relief is high enough, no space-heating
# demand is generated.
#
# Why normalization is applied
# ----------------------------
# In this model, q_dot_heat,raw(t) is not an exact building-physics proof, but an
# hourly distribution indicator. It is therefore normalized to the known annual
# space-heating demand:
#
#     q_dot_heat(t)
#       = Q_heat,year * q_dot_heat,raw(t) / sum_t(q_dot_heat,raw(t) * Δt)
#
# With hourly resolution, Δt = 1 h. Therefore:
#
#     sum_t(q_dot_heat(t) * 1 h) = Q_heat,year
#
# This normalization ensures that additional profile factors such as user
# behavior, night setback, solar gains, surface-to-volume ratio, or thermal
# capacity change the temporal distribution, but not the specified annual energy
# amount.
#
# Meaning of the model parameters
# -------------------------------
# 1) Surface-to-volume ratio A/V:
#    The heated floor area and room height are used to estimate the building
#    volume. A/V then gives an approximate envelope area. A larger envelope area
#    increases H_loss and, in this model, additionally emphasizes cold hours.
#
# 2) Window area fraction:
#    The window fraction affects two effects:
#    - higher transmission losses through windows,
#    - higher usable solar gains under global irradiance.
#
# 3) Thermal capacity "light", "medium", "heavy":
#    The classes are interpreted as a simplified 1R1C behavior:
#    lightweight buildings react faster, while heavy buildings delay and smooth
#    temperature and solar effects more strongly. Technically, this is represented
#    by exponential filters with different time constants.
#
# 4) Night setback:
#    When night setback is enabled, the room-air setpoint is reduced during the
#    selected time window. This yields a lower balance temperature T_balance(t).
#    As a result, night loads decrease, while part of the load may shift into
#    later reheating hours.
#
# 5) Domestic hot water:
#    The domestic-hot-water demand is distributed independently of outdoor air
#    temperature as a daily profile with morning, noon, and evening peaks, and is
#    also normalized exactly to the annual domestic-hot-water energy.
#
# 6) Stochastic user behavior:
#    Random daily, hourly, and vacation modifiers represent individual usage.
#    The variability decreases with heated floor area because many households in
#    larger buildings statistically compensate for each other.
#
# Sources used or considered
# --------------------------
# - EN ISO 52016-1:2017:
#   Energy performance of buildings. It contains methods for determining heating
#   and cooling energy demand, indoor temperatures, and heating/cooling loads on
#   an hourly or monthly basis. The model used here is intentionally much simpler,
#   but follows the concept of an hourly heat balance.
#
# - DIN V 18599 / DIN/TS 18599:
#   German standards series for the energy performance assessment of residential
#   and non-residential buildings. It serves as a reference for the principle of
#   a building-related energy balance. This script is not a normative
#   DIN V 18599 assessment.
#
# - VDI 4655:
#   Reference load profiles for residential buildings for electricity, heating,
#   and domestic hot water. It motivates the use of synthetic load profiles and
#   typical daily patterns, especially for domestic hot water and household use.
#
# - Heating-degree-hour / degree-hour principle:
#   Distributing space-heating demand via positive temperature differences
#   T_balance - T_out is a simplified form of the heating-degree-hour approach.
#   This approach is particularly useful when an annual demand is known but no
#   detailed multi-zone building simulation is performed.
#
# Note
# ----
# The script is a plausibility-oriented load-profile model for scenarios,
# comparisons, and preliminary sizing. It does not replace a standards-compliant
# energy-demand calculation, a detailed thermal building simulation, or a heating
# load calculation according to DIN EN 12831.
# =============================================================================

# =============================================================================
# EPW weather-data import
# =============================================================================
#
# EnergyPlus Weather Files (*.epw) contain hourly weather records after 8 header
# lines. This heat-load model mainly uses:
#
# - Dry Bulb Temperature [°C]:
#   outdoor air temperature; EPW column 7 according to the EnergyPlus
#   documentation.
#
# - Global Horizontal Radiation [Wh/m²]:
#   global horizontal radiant energy per time interval; EPW column 14.
#   For hourly EPW data, 1 Wh/m² per hour corresponds to an average irradiance
#   of 1 W/m². Therefore, for 1-h time steps, this value can be used directly as
#   average global horizontal irradiance in W/m².
#
# Note on time convention:
# EPW timestamps are usually encoded as hour-ending values
# (hour = 1 ... 24, minute often = 60). For load-profile models, a continuous
# 8760-h index starting at 01-01 00:00 is usually more practical. This is what
# read_epw_weather(..., reset_index_to_continuous_year=True) does.
# To evaluate the original EPW time convention, set
# reset_index_to_continuous_year=False.
# =============================================================================

EPW_COLUMNS = [
    "year", "month", "day", "hour", "minute", "data_source_uncertainty_flags",
    "dry_bulb_temperature_C", "dew_point_temperature_C", "relative_humidity_percent",
    "atmospheric_station_pressure_Pa", "extraterrestrial_horizontal_radiation_Wh_m2",
    "extraterrestrial_direct_normal_radiation_Wh_m2",
    "horizontal_infrared_radiation_intensity_Wh_m2",
    "global_horizontal_radiation_Wh_m2", "direct_normal_radiation_Wh_m2",
    "diffuse_horizontal_radiation_Wh_m2", "global_horizontal_illuminance_lux",
    "direct_normal_illuminance_lux", "diffuse_horizontal_illuminance_lux",
    "zenith_luminance_cd_m2", "wind_direction_deg", "wind_speed_m_s",
    "total_sky_cover_tenths", "opaque_sky_cover_tenths", "visibility_km",
    "ceiling_height_m", "present_weather_observation", "present_weather_codes",
    "precipitable_water_mm", "aerosol_optical_depth_thousandths", "snow_depth_cm",
    "days_since_last_snowfall", "albedo", "liquid_precipitation_depth_mm",
    "liquid_precipitation_quantity_hr",
]


def read_epw_location(epw_file: str | Path) -> dict:
    """
    Reads location information from the LOCATION line of an EPW file.
    """
    epw_file = Path(epw_file)

    with epw_file.open("r", encoding="utf-8", errors="replace") as f:
        location_line = f.readline().strip()

    parts = location_line.split(",")

    if len(parts) < 10 or parts[0].upper() != "LOCATION":
        return {}

    def _float_or_none(value: str):
        try:
            return float(value)
        except Exception:
            return None

    return {
        "city": parts[1],
        "state_province_region": parts[2],
        "country": parts[3],
        "data_source": parts[4],
        "wmo_number": parts[5],
        "latitude_deg": _float_or_none(parts[6]),
        "longitude_deg": _float_or_none(parts[7]),
        "time_zone": _float_or_none(parts[8]),
        "elevation_m": _float_or_none(parts[9]),
    }


def read_epw_weather(
    epw_file: str | Path,
    *,
    reset_index_to_continuous_year: bool = True,
    model_year: int | None = None,
) -> pd.DataFrame:
    """
    Reads an EnergyPlus EPW file and returns the climate data required by the
    heat-load model.

    Returned DataFrame:
        Index:
            hourly DatetimeIndex

        Columns:
            T_a:
                outdoor air temperature [°C]

            GHI:
                average global horizontal irradiance [W/m²]
                Derived from the EPW column Global Horizontal Radiation [Wh/m²].
                For 1-h time steps, Wh/m² per hour is numerically identical to
                W/m² as an hourly average.

            dry_bulb_temperature_C:
                identical to T_a, additionally provided with the EPW name.

            global_horizontal_radiation_Wh_m2:
                original EPW radiant energy per hour.
    """
    epw_file = Path(epw_file)

    if not epw_file.exists():
        raise FileNotFoundError(f"EPW file not found: {epw_file}")

    raw = pd.read_csv(
        epw_file,
        skiprows=8,
        header=None,
        names=EPW_COLUMNS,
        na_values=["", "?", "NA"],
    )

    if len(raw) == 0:
        raise ValueError("EPW file contains no weather data rows.")

    # Numeric conversion of the required columns.
    for col in [
        "year", "month", "day", "hour", "minute",
        "dry_bulb_temperature_C",
        "global_horizontal_radiation_Wh_m2",
    ]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")

    # EPW missing-value conventions:
    # Dry Bulb: 99.9 as missing; GHI: 9999 as missing.
    t = raw["dry_bulb_temperature_C"].copy()
    t = t.mask((t >= 99.0) | (t <= -99.0))

    ghi = raw["global_horizontal_radiation_Wh_m2"].copy()
    ghi = ghi.mask(ghi >= 9999)
    ghi = ghi.clip(lower=0)

    # Interpolate missing values over time, if present.
    t = t.interpolate(limit_direction="both")
    ghi = ghi.interpolate(limit_direction="both").fillna(0).clip(lower=0)

    if reset_index_to_continuous_year:
        # Practical for modeling and plotting:
        # 8760 continuous hours starting at 01-01 00:00.
        year = int(model_year or raw["year"].dropna().iloc[0])
        index = pd.date_range(
            start=f"{year}-01-01 00:00",
            periods=len(raw),
            freq="h",
        )
    else:
        # Convert the EPW hour-ending convention to start timestamps:
        # hour=1 -> 00:00, hour=24 -> 23:00.
        base_date = pd.to_datetime(
            {
                "year": raw["year"].astype(int),
                "month": raw["month"].astype(int),
                "day": raw["day"].astype(int),
            },
            errors="coerce",
        )
        index = base_date + pd.to_timedelta(raw["hour"].astype(int) - 1, unit="h")

    weather = pd.DataFrame(
        {
            "T_a": t.to_numpy(dtype=float),
            "GHI": ghi.to_numpy(dtype=float),  # Wh/m² per h = W/m² hourly average
            "dry_bulb_temperature_C": t.to_numpy(dtype=float),
            "global_horizontal_radiation_Wh_m2": ghi.to_numpy(dtype=float),
        },
        index=index,
    )

    weather.index.name = "time"

    location = read_epw_location(epw_file)
    weather.attrs["source_file"] = str(epw_file)
    weather.attrs["source_format"] = "EnergyPlus EPW"
    weather.attrs["location"] = location
    weather.attrs["annual_GHI_kWh_m2"] = float(weather["GHI"].sum() / 1000.0)
    weather.attrs["mean_temperature_C"] = float(weather["T_a"].mean())

    return weather



THERMAL_CAPACITY_CLASSES = {
    "light": {
        "tau_temperature_h": 1.5,
        "tau_solar_h": 2.0,
        "solar_utilisation": 0.55,
        "load_smoothing_h": 1.0,
    },
    "medium": {
        "tau_temperature_h": 4.0,
        "tau_solar_h": 6.0,
        "solar_utilisation": 0.70,
        "load_smoothing_h": 2.5,
    },
    "heavy": {
        "tau_temperature_h": 10.0,
        "tau_solar_h": 14.0,
        "solar_utilisation": 0.85,
        "load_smoothing_h": 5.0,
    },
}


def exponential_filter(series: pd.Series, tau_h: float) -> pd.Series:
    """
    Exponential smoothing of an hourly time series.
    Larger tau_h values represent higher thermal inertia.
    """
    if tau_h <= 0:
        return series.copy()

    alpha = 1.0 - np.exp(-1.0 / tau_h)
    return series.ewm(alpha=alpha, adjust=False).mean()


def dhw_weight_with_peaks(
    index: pd.DatetimeIndex,
    n: int,
    *,
    weekend_factor: float = 1.08,
) -> pd.Series:
    """
    Domestic-hot-water profile with morning, noon, and evening peaks.

    The values are weighting factors.
    The annual energy is later normalized exactly to annual_dhw_kwh.
    """
    hour = index.hour.to_numpy() + index.minute.to_numpy() / 60
    dayofweek = index.dayofweek.to_numpy()
    is_weekend = dayofweek >= 5

    morning_center = np.where(is_weekend, 8.5, 7.0)
    noon_center = np.where(is_weekend, 13.0, 12.3)
    evening_center = np.where(is_weekend, 20.5, 19.8)

    base = np.full(n, 0.18)

    morning_peak = 1.45 * np.exp(-0.5 * ((hour - morning_center) / 1.15) ** 2)
    noon_peak = 0.65 * np.exp(-0.5 * ((hour - noon_center) / 1.70) ** 2)
    evening_peak = 1.25 * np.exp(-0.5 * ((hour - evening_center) / 1.90) ** 2)

    weight = base + morning_peak + noon_peak + evening_peak
    weight *= np.where(is_weekend, weekend_factor, 1.0)

    return pd.Series(weight, index=index)


def area_dependent_fluctuation_factor(
    heated_floor_area_m2: float,
    *,
    reference_area_m2: float = 80.0,
    exponent: float = 0.5,
    min_factor: float = 0.15,
    max_factor: float = 1.80,
) -> float:
    """
    Scales the magnitude of user-behavior fluctuations with heated floor area.

    Small buildings:
        stronger individual fluctuations

    Large buildings:
        smaller fluctuations due to statistical compensation
    """
    if heated_floor_area_m2 <= 0:
        raise ValueError("heated_floor_area_m2 must be positive.")

    factor = (reference_area_m2 / heated_floor_area_m2) ** exponent
    return float(np.clip(factor, min_factor, max_factor))


def generate_user_behavior_modifiers(
    index: pd.DatetimeIndex,
    heated_floor_area_m2: float,
    *,
    random_seed: int | None = None,
    behavior_strength: float = 1.0,
    reference_area_m2: float = 80.0,
    vacation_days_per_year: int = 18,
    vacation_blocks_per_year: int = 2,
    vacation_heating_reduction: float = 0.35,
    vacation_dhw_reduction: float = 0.85,
) -> pd.DataFrame:
    """
    Generates hourly random modifiers for user behavior.

    The modifiers only affect the temporal distribution.
    The annual energy is normalized exactly afterwards.
    """
    if not isinstance(index, pd.DatetimeIndex):
        raise ValueError("User-behavior modeling requires a DatetimeIndex.")

    if behavior_strength < 0:
        raise ValueError("behavior_strength must not be negative.")

    n = len(index)
    rng = np.random.default_rng(random_seed)

    area_factor = area_dependent_fluctuation_factor(
        heated_floor_area_m2,
        reference_area_m2=reference_area_m2,
    )
    strength = behavior_strength * area_factor

    hour = index.hour.to_numpy()
    dayofweek = index.dayofweek.to_numpy()
    is_weekend = dayofweek >= 5

    morning_presence = np.exp(-0.5 * ((hour - 7.0) / 1.8) ** 2)
    evening_presence = np.exp(-0.5 * ((hour - 19.5) / 2.8) ** 2)
    night_setback = np.exp(-0.5 * ((hour - 3.0) / 2.5) ** 2)
    midday_presence = np.exp(-0.5 * ((hour - 13.0) / 2.2) ** 2)

    weekday_shape = (
        1.00
        + 0.10 * morning_presence
        + 0.16 * evening_presence
        - 0.10 * night_setback
        - 0.05 * midday_presence
    )

    weekend_shape = (
        1.00
        + 0.08 * morning_presence
        + 0.12 * midday_presence
        + 0.14 * evening_presence
        - 0.06 * night_setback
    )

    space_daily_shape = np.where(is_weekend, weekend_shape, weekday_shape)
    space_daily_shape = space_daily_shape / np.mean(space_daily_shape)

    dhw_daily_shape = (
        1.00
        + 0.18 * morning_presence
        + 0.10 * midday_presence
        + 0.16 * evening_presence
    )
    dhw_daily_shape = dhw_daily_shape / np.mean(dhw_daily_shape)

    unique_days = pd.Index(index.normalize().unique())
    ndays = len(unique_days)

    daily_random = np.zeros(ndays)
    x = 0.0
    for i in range(ndays):
        x = 0.70 * x + rng.normal(0.0, 0.18)
        daily_random[i] = x

    daily_random = np.clip(daily_random, -0.45, 0.45)

    day_lookup = pd.Series(np.arange(ndays), index=unique_days)
    day_index = day_lookup.loc[index.normalize()].to_numpy()

    daily_factor = 1.0 + strength * daily_random[day_index]

    hourly_noise_space = rng.normal(0.0, 0.04 * strength, n)
    hourly_noise_dhw = rng.normal(0.0, 0.16 * strength, n)

    hourly_factor_space = np.clip(1.0 + hourly_noise_space, 0.50, 1.60)
    hourly_factor_dhw = np.clip(1.0 + hourly_noise_dhw, 0.20, 2.20)

    vacation_day_factor = np.ones(ndays)

    if vacation_days_per_year > 0 and vacation_blocks_per_year > 0:
        remaining_days = vacation_days_per_year

        for _ in range(vacation_blocks_per_year):
            if remaining_days <= 0:
                break

            block_length = max(
                2,
                int(round(rng.normal(
                    vacation_days_per_year / vacation_blocks_per_year,
                    2.0,
                )))
            )

            block_length = min(block_length, remaining_days)
            start_day = int(rng.integers(0, max(1, ndays - block_length)))

            vacation_day_factor[start_day:start_day + block_length] = 0.0
            remaining_days -= block_length

    is_vacation_hour = vacation_day_factor[day_index] < 0.5
    vacation_effect = np.clip(strength, 0.0, 1.0)

    space_vacation_factor = np.where(
        is_vacation_hour,
        1.0 - vacation_heating_reduction * vacation_effect,
        1.0,
    )

    dhw_vacation_factor = np.where(
        is_vacation_hour,
        1.0 - vacation_dhw_reduction * vacation_effect,
        1.0,
    )

    space_user_modifier = (
        space_daily_shape
        * daily_factor
        * hourly_factor_space
        * space_vacation_factor
    )

    dhw_user_modifier = (
        dhw_daily_shape
        * daily_factor
        * hourly_factor_dhw
        * dhw_vacation_factor
    )

    space_user_modifier = np.clip(space_user_modifier, 0.25, 2.20)
    dhw_user_modifier = np.clip(dhw_user_modifier, 0.02, 3.50)

    return pd.DataFrame(
        {
            "space_user_modifier": space_user_modifier,
            "dhw_user_modifier": dhw_user_modifier,
            "is_vacation": is_vacation_hour.astype(int),
        },
        index=index,
    )


def resolve_dhw_energy_kwh(
    annual_energy_kwh: float,
    heated_floor_area_m2: float,
    *,
    dhw_annual_kwh: float | None = None,
    dhw_specific_kwh_m2a: float | None = 12.5,
    dhw_share: float | None = None,
) -> float:
    """
    Determines the annual domestic-hot-water energy.

    Priority:
    1. dhw_annual_kwh
    2. dhw_specific_kwh_m2a * heated_floor_area_m2
    3. dhw_share * annual_energy_kwh
    """
    if dhw_annual_kwh is not None:
        dhw = float(dhw_annual_kwh)
    elif dhw_specific_kwh_m2a is not None:
        dhw = heated_floor_area_m2 * dhw_specific_kwh_m2a
    elif dhw_share is not None:
        dhw = annual_energy_kwh * dhw_share
    else:
        raise ValueError(
            "Specify either dhw_annual_kwh, dhw_specific_kwh_m2a, or dhw_share."
        )

    if dhw < 0:
        raise ValueError("Domestic-hot-water energy must not be negative.")

    if dhw > annual_energy_kwh:
        raise ValueError("Domestic-hot-water energy is greater than the total annual energy demand.")

    return dhw



def make_room_air_setpoint_series(
    index: pd.DatetimeIndex,
    *,
    use_night_setback: bool = False,
    occupied_room_temp_C: float = 20.0,
    night_setback_room_temp_C: float = 15.0,
    night_setback_start_hour: int = 22,
    night_setback_end_hour: int = 6,
) -> pd.DataFrame:
    """
    Creates an hourly room-air setpoint profile.

    use_night_setback=False:
        constant room-air temperature occupied_room_temp_C.

    use_night_setback=True:
        setback between night_setback_start_hour and night_setback_end_hour to
        night_setback_room_temp_C.

    Example:
        start=22, end=6 means 22:00 to 05:59.
    """
    if not isinstance(index, pd.DatetimeIndex):
        raise ValueError("Night setback modeling requires a DatetimeIndex.")

    if not 0 <= night_setback_start_hour <= 23:
        raise ValueError("night_setback_start_hour must be between 0 and 23.")

    if not 0 <= night_setback_end_hour <= 23:
        raise ValueError("night_setback_end_hour must be between 0 and 23.")

    hour = index.hour.to_numpy()

    if not use_night_setback:
        is_night_setback = np.zeros(len(index), dtype=bool)
    else:
        if night_setback_start_hour < night_setback_end_hour:
            is_night_setback = (
                (hour >= night_setback_start_hour)
                & (hour < night_setback_end_hour)
            )
        else:
            # Interval across midnight, e.g. 22 to 6
            is_night_setback = (
                (hour >= night_setback_start_hour)
                | (hour < night_setback_end_hour)
            )

    room_air_setpoint_C = np.where(
        is_night_setback,
        night_setback_room_temp_C,
        occupied_room_temp_C,
    )

    return pd.DataFrame(
        {
            "room_air_setpoint_C": room_air_setpoint_C,
            "is_night_setback": is_night_setback.astype(int),
        },
        index=index,
    )


def calculate_hourly_heat_load_advanced(
    annual_energy_kwh: float,
    outdoor_temp_C,
    global_irradiance_W_m2,
    *,
    heated_floor_area_m2: float,
    surface_volume_ratio_m_inv: float,
    window_area_fraction: float = 0.30,
    thermal_capacity: str = "light",

    # Domestic hot water
    dhw_annual_kwh: float | None = None,
    dhw_specific_kwh_m2a: float | None = 12.5,
    dhw_share: float | None = None,

    # Building model
    room_height_m: float = 2.6,
    facade_area_fraction_of_envelope: float = 0.65,
    u_opaque_W_m2K: float = 0.35,
    u_window_W_m2K: float = 1.30,
    air_change_rate_h_inv: float = 0.35,

    # Heating and solar model
    heating_balance_temp_C: float = 15.0,
    solar_g_value: float = 0.55,
    solar_orientation_factor: float = 0.55,
    reference_av_ratio_m_inv: float = 0.55,
    av_shape_sensitivity: float = 0.25,

    # User behavior
    use_random_user_behavior: bool = False,
    random_seed: int | None = None,
    behavior_strength: float = 1.0,
    vacation_days_per_year: int = 18,
    vacation_blocks_per_year: int = 2,

    # Optional night setback of the room-air temperature
    use_night_setback: bool = False,
    occupied_room_temp_C: float = 20.0,
    night_setback_room_temp_C: float = 15.0,
    night_setback_start_hour: int = 22,
    night_setback_end_hour: int = 6,
    setback_balance_sensitivity: float = 1.0,
) -> pd.DataFrame:
    """
    Calculates hourly heat-load time series for space heating and domestic hot
    water.

    At hourly resolution, the sum of total_heat_load_kW over all hours equals
    the specified annual energy demand in kWh.
    """
    if annual_energy_kwh <= 0:
        raise ValueError("annual_energy_kwh must be positive.")

    if heated_floor_area_m2 <= 0:
        raise ValueError("heated_floor_area_m2 must be positive.")

    if surface_volume_ratio_m_inv <= 0:
        raise ValueError("surface_volume_ratio_m_inv must be positive.")

    if not 0 <= window_area_fraction <= 0.90:
        raise ValueError("window_area_fraction should be between 0 and 0.90.")

    if thermal_capacity not in THERMAL_CAPACITY_CLASSES:
        raise ValueError("thermal_capacity must be 'light', 'medium', or 'heavy'.")

    params = THERMAL_CAPACITY_CLASSES[thermal_capacity]

    t = pd.Series(outdoor_temp_C).astype(float)
    g = pd.Series(global_irradiance_W_m2).astype(float)

    if len(t) != len(g):
        raise ValueError("Temperature and irradiance time series must have the same length.")

    if not t.index.equals(g.index):
        g.index = t.index

    if t.isna().any():
        raise ValueError("Outdoor air temperature contains missing values.")

    if g.isna().any():
        raise ValueError("Global irradiance contains missing values.")

    g = g.clip(lower=0)
    n = len(t)

    # Geometry
    building_volume_m3 = heated_floor_area_m2 * room_height_m
    envelope_area_m2 = surface_volume_ratio_m_inv * building_volume_m3

    facade_area_m2 = facade_area_fraction_of_envelope * envelope_area_m2
    window_area_m2 = window_area_fraction * facade_area_m2
    opaque_envelope_area_m2 = max(envelope_area_m2 - window_area_m2, 0.0)

    h_transmission_W_K = (
        u_opaque_W_m2K * opaque_envelope_area_m2
        + u_window_W_m2K * window_area_m2
    )

    h_ventilation_W_K = 0.34 * air_change_rate_h_inv * building_volume_m3
    h_total_W_K = h_transmission_W_K + h_ventilation_W_K

    # Annual energy split
    annual_dhw_kwh = resolve_dhw_energy_kwh(
        annual_energy_kwh,
        heated_floor_area_m2,
        dhw_annual_kwh=dhw_annual_kwh,
        dhw_specific_kwh_m2a=dhw_specific_kwh_m2a,
        dhw_share=dhw_share,
    )

    annual_space_heating_kwh = annual_energy_kwh - annual_dhw_kwh

    # Space-heating indicator
    effective_outdoor_temp_C = exponential_filter(
        t,
        tau_h=params["tau_temperature_h"],
    )

    # Optional night setback of the room-air temperature.
    # heating_balance_temp_C is the balance temperature at occupied_room_temp_C.
    # With night setback, the balance temperature is reduced accordingly.
    setpoint_profile = make_room_air_setpoint_series(
        t.index,
        use_night_setback=use_night_setback,
        occupied_room_temp_C=occupied_room_temp_C,
        night_setback_room_temp_C=night_setback_room_temp_C,
        night_setback_start_hour=night_setback_start_hour,
        night_setback_end_hour=night_setback_end_hour,
    )

    room_air_setpoint_C = setpoint_profile["room_air_setpoint_C"]
    is_night_setback = setpoint_profile["is_night_setback"]

    dynamic_heating_balance_temp_C = (
        heating_balance_temp_C
        + setback_balance_sensitivity
        * (room_air_setpoint_C - occupied_room_temp_C)
    )

    heating_degree_K = (
        dynamic_heating_balance_temp_C - effective_outdoor_temp_C
    ).clip(lower=0)

    positive_hdg = heating_degree_K[heating_degree_K > 0]
    mean_hdg = positive_hdg.mean() if len(positive_hdg) > 0 else 1.0

    av_ratio = surface_volume_ratio_m_inv / reference_av_ratio_m_inv
    av_exponent = av_shape_sensitivity * (av_ratio - 1.0)
    av_exponent = float(np.clip(av_exponent, -0.35, 0.65))

    temperature_intensity = (heating_degree_K / mean_hdg).clip(lower=0.05, upper=4.0)
    av_dynamic_shape_factor = temperature_intensity ** av_exponent

    # ------------------------------------------------------------------
    # Physically motivated space-heating indicator
    # ------------------------------------------------------------------
    # h_total_W_K * heating_degree_K describes the sensible heat output that
    # would be required to maintain the balance temperature at the current
    # thermally effective outdoor air temperature.
    #
    # In the steady-state sense, the A/V ratio already affects the envelope
    # area and therefore h_total_W_K. In addition, a small dynamic shape
    # correction av_dynamic_shape_factor is used here: buildings with a large
    # A/V ratio react more strongly in cold hours, while compact buildings are
    # somewhat smoother.
    #
    # Division by 1000 converts W to kW.
    heat_loss_indicator_kW = (
        h_total_W_K * heating_degree_K * av_dynamic_shape_factor / 1000.0
    )

    # Solar gains are calculated from horizontal global irradiance, approximate
    # window area, g-value, orientation/shading factor, and
    # utilization factor. The subsequent exponential filtering represents
    # the delayed usability of solar gains in the building mass.
    raw_solar_gain_kW = (
        g / 1000.0
        * window_area_m2
        * solar_g_value
        * solar_orientation_factor
        * params["solar_utilisation"]
    )

    usable_solar_gain_kW = exponential_filter(
        raw_solar_gain_kW,
        tau_h=params["tau_solar_h"],
    )

    space_heating_indicator_kW = (
        heat_loss_indicator_kW - usable_solar_gain_kW
    ).clip(lower=0)

    space_heating_indicator_kW = exponential_filter(
        space_heating_indicator_kW,
        tau_h=params["load_smoothing_h"],
    )

    # User behavior
    if use_random_user_behavior:
        user_behavior = generate_user_behavior_modifiers(
            t.index,
            heated_floor_area_m2=heated_floor_area_m2,
            random_seed=random_seed,
            behavior_strength=behavior_strength,
            vacation_days_per_year=vacation_days_per_year,
            vacation_blocks_per_year=vacation_blocks_per_year,
        )

        space_user_modifier = user_behavior["space_user_modifier"]
        dhw_user_modifier = user_behavior["dhw_user_modifier"]
        is_vacation = user_behavior["is_vacation"]
    else:
        space_user_modifier = pd.Series(np.ones(n), index=t.index)
        dhw_user_modifier = pd.Series(np.ones(n), index=t.index)
        is_vacation = pd.Series(np.zeros(n, dtype=int), index=t.index)

    space_heating_indicator_kW = space_heating_indicator_kW * space_user_modifier

    # ------------------------------------------------------------------
    # Normalize space heating to the known annual space-heating demand
    # ------------------------------------------------------------------
    # Up to this point, space_heating_indicator_kW is a relative, physically
    # motivated distribution indicator. Multiplying it by the factor
    #
    #     annual_space_heating_kwh / sum(space_heating_indicator_kW)
    #
    # gives each hour a power value in kW whose sum over 8760 hours equals
    # annual_space_heating_kwh exactly. This keeps the annual demand and input
    # budget consistent, while the parameters only shape the profile.
    if annual_space_heating_kwh > 0:
        if space_heating_indicator_kW.sum() <= 0:
            raise ValueError("Space-heating indicator is zero for all hours.")

        space_heating_load_kW = (
            annual_space_heating_kwh
            * space_heating_indicator_kW
            / space_heating_indicator_kW.sum()
        )
    else:
        space_heating_load_kW = pd.Series(np.zeros(n), index=t.index)

    # ------------------------------------------------------------------
    # Domestic-hot-water profile
    # ------------------------------------------------------------------
    # Domestic hot water is only weakly dependent on outdoor air temperature.
    # Therefore, the annual domestic-hot-water demand is distributed via a
    # normalized usage profile. The three Gaussian-shaped peaks in
    # dhw_weight_with_peaks represent typical morning, noon, and evening usage.
    # The stochastic dhw_user_modifier varies this profile without changing the
    # annual energy.
    dhw_weight = dhw_weight_with_peaks(t.index, n) * dhw_user_modifier

    if annual_dhw_kwh > 0:
        if dhw_weight.sum() <= 0:
            raise ValueError("Domestic-hot-water profile has a zero sum.")

        dhw_load_kW = annual_dhw_kwh * dhw_weight / dhw_weight.sum()
    else:
        dhw_load_kW = pd.Series(np.zeros(n), index=t.index)

    total_heat_load_kW = space_heating_load_kW + dhw_load_kW

    result = pd.DataFrame(
        {
            "outdoor_temp_C": t,
            "global_irradiance_W_m2": g,
            "effective_outdoor_temp_C": effective_outdoor_temp_C,
            "room_air_setpoint_C": room_air_setpoint_C,
            "dynamic_heating_balance_temp_C": dynamic_heating_balance_temp_C,
            "is_night_setback": is_night_setback,
            "heating_degree_K": heating_degree_K,
            "heat_loss_indicator_kW": heat_loss_indicator_kW,
            "usable_solar_gain_kW": usable_solar_gain_kW,
            "space_user_modifier": space_user_modifier,
            "dhw_user_modifier": dhw_user_modifier,
            "is_vacation": is_vacation,
            "space_heating_load_kW": space_heating_load_kW,
            "dhw_load_kW": dhw_load_kW,
            "total_heat_load_kW": total_heat_load_kW,
        }
    )

    result.attrs["annual_energy_input_kWh"] = float(annual_energy_kwh)
    result.attrs["annual_space_heating_kWh"] = float(space_heating_load_kW.sum())
    result.attrs["annual_dhw_kWh"] = float(dhw_load_kW.sum())
    result.attrs["annual_total_kWh"] = float(total_heat_load_kW.sum())
    result.attrs["heated_floor_area_m2"] = float(heated_floor_area_m2)
    result.attrs["specific_annual_energy_kWh_m2a"] = float(
        annual_energy_kwh / heated_floor_area_m2
    )
    result.attrs["surface_volume_ratio_m_inv"] = float(surface_volume_ratio_m_inv)
    result.attrs["window_area_fraction"] = float(window_area_fraction)
    result.attrs["thermal_capacity"] = thermal_capacity
    result.attrs["h_total_W_K"] = float(h_total_W_K)
    result.attrs["use_random_user_behavior"] = bool(use_random_user_behavior)
    result.attrs["random_seed"] = random_seed
    result.attrs["use_night_setback"] = bool(use_night_setback)
    result.attrs["occupied_room_temp_C"] = float(occupied_room_temp_C)
    result.attrs["night_setback_room_temp_C"] = float(night_setback_room_temp_C)
    result.attrs["night_setback_start_hour"] = int(night_setback_start_hour)
    result.attrs["night_setback_end_hour"] = int(night_setback_end_hour)
    result.attrs["setback_balance_sensitivity"] = float(setback_balance_sensitivity)
    result.attrs["area_behavior_factor"] = area_dependent_fluctuation_factor(
        heated_floor_area_m2
    )

    return result


def run_example():
    """
    Example calculation for 3 buildings with 120 m² usable heated area each.
    """
    weather_path = Path("Berlin_mean_climate.csv")

    if not weather_path.exists():
        raise FileNotFoundError(
            "Weather file not found. "
        )

    weather = pd.read_csv(weather_path, parse_dates=["time"]).set_index("time")

    heated_floor_area_m2 = 120.0
    specific_annual_energy_kWh_m2a = 120.0
    annual_energy_kwh = heated_floor_area_m2 * specific_annual_energy_kWh_m2a

    common_kwargs = dict(
        annual_energy_kwh=annual_energy_kwh,
        outdoor_temp_C=weather["T_a"],
        global_irradiance_W_m2=weather["GHI"],
        heated_floor_area_m2=heated_floor_area_m2,
        surface_volume_ratio_m_inv=0.70,
        window_area_fraction=0.20,
        thermal_capacity="mean",
        dhw_specific_kwh_m2a=12.5,
        use_random_user_behavior=True,
        behavior_strength=1.0,
    )

    seeds = [11, 22, 33]
    results = {}

    for i, seed in enumerate(seeds, start=1):
        results[f"Building {i}"] = calculate_hourly_heat_load_advanced(
            **common_kwargs,
            random_seed=seed,
        )

    export = pd.DataFrame(index=weather.index)
    export["outdoor_temp_C"] = weather["T_a"]
    export["global_irradiance_W_m2"] = weather["GHI"]

    summary = []

    for name, df in results.items():
        prefix = name.lower().replace("ä", "ae").replace(" ", "_")

        export[f"{prefix}_space_heating_load_kW"] = df["space_heating_load_kW"]
        export[f"{prefix}_dhw_load_kW"] = df["dhw_load_kW"]
        export[f"{prefix}_total_heat_load_kW"] = df["total_heat_load_kW"]
        export[f"{prefix}_space_user_modifier"] = df["space_user_modifier"]
        export[f"{prefix}_dhw_user_modifier"] = df["dhw_user_modifier"]
        export[f"{prefix}_is_vacation"] = df["is_vacation"]

        summary.append(
            {
                "Building": name,
                "Seed": df.attrs["random_seed"],
                "Annual_energy_kWh_a": round(df["total_heat_load_kW"].sum(), 1),
                "Space_heating_kWh_a": round(df["space_heating_load_kW"].sum(), 1),
                "Domestic_hot_water_kWh_a": round(df["dhw_load_kW"].sum(), 1),
                "Max_total_heat_load_kW": round(df["total_heat_load_kW"].max(), 2),
                "Max_space_heating_kW": round(df["space_heating_load_kW"].max(), 2),
            }
        )

    export = export.reset_index().rename(columns={"index": "time"})
    export.to_csv("heatingLoad.csv", index=False)

    summary_df = pd.DataFrame(summary)
    summary_df.to_csv("heatingLoad_summary.csv", index=False)

    period = slice("2021-01-01 00:00", "2021-01-14 23:00")

    total_plot_df = pd.DataFrame(
        {
            name: df.loc[period, "total_heat_load_kW"]
            for name, df in results.items()
        }
    )

    space_plot_df = pd.DataFrame(
        {
            name: df.loc[period, "space_heating_load_kW"]
            for name, df in results.items()
        }
    )

    plt.figure(figsize=(14, 6))
    for col in total_plot_df.columns:
        plt.plot(total_plot_df.index, total_plot_df[col], label=col)
    plt.title(
        "Hourly total heat load for the first two weeks of January\n"
        "3 buildings of 120 m² each with stochastic user behavior"
    )
    plt.xlabel("Time")
    plt.ylabel("Total heat load [kW]")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("total_heatingLoad_3_buildigs.png", dpi=180)

    plt.figure(figsize=(14, 6))
    for col in space_plot_df.columns:
        plt.plot(space_plot_df.index, space_plot_df[col], label=col)
    plt.title(
        "Hourly space-heating load for the first two weeks of January\n"
        "without domestic hot water, 3 buildings of 120 m² each"
    )
    plt.xlabel("Time")
    plt.ylabel("Space-heating load [kW]")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("individual_heatingLoad_3_buildings.png", dpi=180)

    print(summary_df.to_string(index=False))




def run_epw_example():
    """
    Example calculation with an EnergyPlus EPW file.

    Expected input file:
        HOSTRADA_Berlin2025.epw

    Generated files:
        epw_wetter_extracted.csv
        heatingLoad.csv
        heatingLoad.png
    """
    epw_path = Path("HOSTRADA_Berlin2025.epw")

    if not epw_path.exists():
        raise FileNotFoundError(
            "EPW file not found. Place HOSTRADA_Berlin2025.epw "
            "in the same folder as this script."
        )

    weather = read_epw_weather(
        epw_path,
        reset_index_to_continuous_year=True,
    )

    # Export the extracted climate data in the previous model format.
    weather_export = weather[["T_a", "GHI"]].reset_index()
    weather_export.to_csv("epw_wetter_extracted.csv", index=False)

    # Example building
    heated_floor_area_m2 = 1000.0
    specific_annual_energy_kWh_m2a = 100.0
    annual_energy_kwh = heated_floor_area_m2 * specific_annual_energy_kWh_m2a

    load = calculate_hourly_heat_load_advanced(
        annual_energy_kwh=annual_energy_kwh,
        outdoor_temp_C=weather["T_a"],
        global_irradiance_W_m2=weather["GHI"],
        heated_floor_area_m2=heated_floor_area_m2,
        surface_volume_ratio_m_inv=0.70,
        window_area_fraction=0.20,
        thermal_capacity="medium",
        dhw_specific_kwh_m2a=12.5,
        use_random_user_behavior=True,
        random_seed=42,
        behavior_strength=1.0,
        use_night_setback=False,
    )

    result = pd.DataFrame(index=weather.index)
    result["T_a"] = weather["T_a"]
    result["GHI"] = weather["GHI"]
    result["space_heating_load_kW"] = load["space_heating_load_kW"]
    result["dhw_load_kW"] = load["dhw_load_kW"]
    result["total_heat_load_kW"] = load["total_heat_load_kW"]

    plt.figure(figsize=(15, 6))
    plt.plot(load.index, load["total_heat_load_kW"], label="Total heat load")
    plt.plot(load.index, load["space_heating_load_kW"], label="Space heating", alpha=0.8)
    plt.title(
        "Annual heat-load profile from EPW climate data\n"
        "Example building: 1000 m², 100 kWh/(m²·a)"
    )
    plt.xlabel("Time")
    plt.ylabel("Heat load [kW]")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("heatingLoad.png", dpi=180)

    summary = pd.DataFrame(
        [
            {
                "Metric": "EPW file",
                "Value": str(epw_path),
            },
            {
                "Metric": "Location",
                "Value": weather.attrs.get("location", {}).get("city", ""),
            },
            {
                "Metric": "Annual mean outdoor air temperature [°C]",
                "Value": round(weather["T_a"].mean(), 2),
            },
            {
                "Metric": "Annual global horizontal radiation [kWh/m²]",
                "Value": round(weather["GHI"].sum() / 1000.0, 1),
            },
            {
                "Metric": "Annual building energy [kWh/a]",
                "Value": round(load["total_heat_load_kW"].sum(), 1),
            },
            {
                "Metric": "Maximum total heat load [kW]",
                "Value": round(load["total_heat_load_kW"].max(), 2),
            },
        ]
    )

    summary.to_csv("heatingLoad.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    run_epw_example()
