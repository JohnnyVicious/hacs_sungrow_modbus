# Sungrow Modbus Register Reference

This document provides a comprehensive inventory of Modbus registers used by Sungrow SHx hybrid inverters, comparing registers documented in the example YAML configuration with those implemented in this integration.

**Important Note on Addressing:**
- The example YAML file uses **0-based addressing** (the `address` field is the register number minus 1)
- Comments in the YAML show the actual **1-based register number** (e.g., `address: 4989 # reg 4990`)
- This integration uses **1-based register numbers** directly
- All registers in this document use **1-based addressing** (the actual Modbus register number)

## Overview

| Category | Input Registers | Holding Registers | Total Implemented |
|----------|----------------|-------------------|-------------------|
| Device Information | 12 | - | 12 |
| PV Information | 14 | - | 14 |
| AC Information | 12 | - | 12 |
| Battery Information | 22 | 6 | 28 |
| Meter Information | 10 | - | 10 |
| Load Information | 8 | - | 8 |
| Grid/Export | 8 | 3 | 11 |
| Status Information | 7 | - | 7 |
| EMS Control | - | 8 | 8 |
| Firmware | 45 | - | 45 |
| Battery Stack (via Slave 200+) | 14 | - | 14 |

---

## Input Registers (Read-Only)

### Device Information (4989-5000)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 4989-4998 | Inverter Serial | string(10) | - | - | No | Yes | Yes | 10 registers as UTF-8 string |
| 4999 | Device Type Code | uint16 | 1 | - | No | Yes | Yes | Identifies inverter model |
| 5000 | Nominal Active Power | uint16 | 0.1 | kW | No | Yes | - | Rated power of inverter |

### PV Generation Summary (5002-5008)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5002 | Daily PV Generation | uint16 | 0.1 | kWh | No | Yes | Yes | Resets at midnight |
| 5003-5004 | Total PV Generation | uint32 | 0.1 | kWh | No | Yes | Yes | Lifetime total, word swap |
| 5005-5006 | Reserved | - | - | - | - | - | - | Reserved registers |
| 5007 | Inverter Temperature | int16 | 0.1 | C | Yes | Yes | Yes | Internal temperature |

### MPPT Data (5011-5018)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5011 | MPPT1 Voltage | uint16 | 0.1 | V | No | Yes | Yes | PV string 1 voltage |
| 5012 | MPPT1 Current | uint16 | 0.1 | A | No | Yes | Yes | PV string 1 current |
| 5013 | MPPT2 Voltage | uint16 | 0.1 | V | No | Yes | Yes | PV string 2 voltage |
| 5014 | MPPT2 Current | uint16 | 0.1 | A | No | Yes | Yes | PV string 2 current |
| 5015 | MPPT3 Voltage | uint16 | 0.1 | V | No | Yes | Commented | Only for T-series with 3 MPPTs |
| 5016 | MPPT3 Current | uint16 | 0.1 | A | No | Yes | Commented | Only for T-series with 3 MPPTs |
| 5017-5018 | Total DC Power | uint32 | 1 | W | No | Yes | Yes | Combined PV power, word swap |

### AC Output Voltages (5018-5020)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5018 | Phase A Voltage | uint16 | 0.1 | V | No | Yes | Yes | All inverters |
| 5019 | Phase B Voltage | uint16 | 0.1 | V | No | Yes | Yes | Three-phase only |
| 5020 | Phase C Voltage | uint16 | 0.1 | V | No | Yes | Yes | Three-phase only |

### AC Output - String Inverters Only (5022-5036)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5022 | Phase A Current | int16 | 0.1 | A | Yes | Yes (string) | - | String inverters (not hybrid) |
| 5023 | Phase B Current | int16 | 0.1 | A | Yes | Yes (string) | - | String inverters, three-phase |
| 5024 | Phase C Current | int16 | 0.1 | A | Yes | Yes (string) | - | String inverters, three-phase |
| 5031-5032 | Total Active Power | uint32 | 1 | W | No | Yes (string) | - | String inverters only |
| 5033-5034 | Reactive Power | int32 | 1 | var | Yes | Yes (string) | - | String inverters |
| 5035 | Power Factor | int16 | 0.001 | % | Yes | Yes (string) | - | String inverters |
| 5036 | Grid Frequency | uint16 | 0.1 | Hz | No | Yes (string) | - | String inverters |
| 5038 | Work State | uint16 | 1 | - | No | Yes (string) | - | String inverters status |

### Reactive Power and Power Factor - Hybrid (5032-5035)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5032-5033 | Reactive Power | int32 | 1 | var | Yes | Yes | Yes | Word swap |
| 5034 | Power Factor | int16 | 0.001 | % | Yes | Yes | Yes | -1.000 to +1.000 |

### Fault Codes (5045-5049)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5045 | Fault Code 1 | uint16 | 1 | - | No | Yes | - | Primary fault |
| 5046 | Fault Code 2 | uint16 | 1 | - | No | Yes | - | Secondary fault |
| 5047 | Fault Code 3 | uint16 | 1 | - | No | Yes | - | Tertiary fault |
| 5048 | Fault Code 4 | uint16 | 1 | - | No | Yes | - | Additional fault |
| 5049 | Fault Code 5 | uint16 | 1 | - | No | Yes | - | Additional fault |

### String Inverter Additional (5049, 5071)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5049 | Nominal Reactive Power | uint16 | 0.1 | kvar | No | Yes (string) | - | String inverters |
| 5071 | Array Insulation Resistance | uint16 | 1 | kohm | No | Yes (string) | - | PV array isolation |

### Grid Frequency - Hybrid (5241)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5241 | Grid Frequency | uint16 | 0.01 | Hz | No | Yes | Yes | Hybrid inverters |

### Meter Data (5600-5608)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5600-5601 | Meter Active Power | int32 | 1 | W | Yes | Yes | Yes | Grid meter power, word swap |
| 5602-5603 | Meter Phase A Active Power | int32 | 1 | W | Yes | Yes | Yes | Word swap |
| 5604-5605 | Meter Phase B Active Power | int32 | 1 | W | Yes | Yes | Yes | Word swap |
| 5606-5607 | Meter Phase C Active Power | int32 | 1 | W | Yes | Yes | Yes | Word swap |

### BMS Data (5627-5639)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5627 | BDC Rated Power | uint16 | 100 | W | No | Yes | Yes | Battery DC converter rating |
| 5634 | BMS Max Charging Current | uint16 | 1 | A | No | Yes | Yes | BMS limit |
| 5635 | BMS Max Discharging Current | uint16 | 1 | A | No | Yes | Yes | BMS limit |
| 5638 | Battery Capacity | uint16 | 0.01 | kWh | No | Yes | Yes | Total battery capacity |

### Backup Power (5722-5727)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5722 | Backup Phase A Power | int16 | 1 | W | Yes | Yes | Yes | Emergency load phase A |
| 5723 | Backup Phase B Power | int16 | 1 | W | Yes | Yes | Yes | Emergency load phase B |
| 5724 | Backup Phase C Power | int16 | 1 | W | Yes | Yes | Yes | Emergency load phase C |
| 5725-5726 | Total Backup Power | int32 | 1 | W | Yes | Yes | Yes | Word swap |

### Meter Voltages and Currents (5740-5746)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5740 | Meter Phase A Voltage | int16 | 0.1 | V | Yes | Yes | Yes | Grid meter |
| 5741 | Meter Phase B Voltage | int16 | 0.1 | V | Yes | Yes | Yes | Grid meter |
| 5742 | Meter Phase C Voltage | int16 | 0.1 | V | Yes | Yes | Yes | Grid meter |
| 5743 | Meter Phase A Current | uint16 | 0.01 | A | No | Yes | Yes | Grid meter |
| 5744 | Meter Phase B Current | uint16 | 0.01 | A | No | Yes | Yes | Grid meter |
| 5745 | Meter Phase C Current | uint16 | 0.01 | A | No | Yes | Yes | Grid meter |

### Monthly/Yearly Statistics (6226-6634) - NOT IMPLEMENTED

These registers are available only on some SH*RT inverters with direct LAN connection (not via WiNet-S).

| Register Range | Name | Data Type | Scale | Unit | Notes |
|----------------|------|-----------|-------|------|-------|
| 6226-6237 | Monthly PV Generation (Jan-Dec) | uint16 | 0.1 | kWh | YAML only (commented) |
| 6257-6277 | Yearly PV Generation (2019-2029) | uint32 | 0.1 | kWh | YAML only (commented) |
| 6595-6606 | Monthly Export (Jan-Dec) | uint16 | 0.1 | kWh | YAML only (commented) |
| 6615-6634 | Yearly Export (2019-2028) | uint32 | 0.1 | kWh | YAML only (commented) |

### System State (12999-13001)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 12999 | System State | uint16 | 1 | - | No | Yes | Yes | See value mapping below |
| 13000 | Running State | uint16 | 1 | - | No | Yes | Yes | Bit-field status |

### PV Energy - Hybrid 13000 Range (13002-13006)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 13002 | Daily PV Energy | uint16 | 0.1 | kWh | No | Yes | Yes | Hybrid register |
| 13003-13004 | Total PV Energy | uint32 | 0.1 | kWh | No | Yes | Yes | Word swap |
| 13005-13006 | Total Consumed Energy | uint32 | 0.1 | kWh | No | Yes | Yes | Word swap |

### Load and Export Power (13007-13019)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 13007-13008 | Load Power | int32 | 1 | W | Yes | Yes | Yes | Word swap |
| 13009-13010 | Export Power | int32 | 1 | W | Yes | Yes | Yes | Positive=export, negative=import |
| 13011 | Daily Battery Charge From PV | uint16 | 0.1 | kWh | No | Yes | Yes | PV-to-battery only |
| 13012-13013 | Total Battery Charge From PV | uint32 | 0.1 | kWh | No | Yes | Yes | Word swap |
| 13016 | Daily Direct Energy Consumption | uint16 | 0.1 | kWh | No | Yes | Yes | PV direct to load |
| 13017-13018 | Total Direct Energy Consumption | uint32 | 0.1 | kWh | No | Yes | Yes | Word swap |

### Battery Status (13020-13028)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 13020 | Battery Voltage | uint16 | 0.1 | V | No | Yes | Yes | Battery pack voltage |
| 13021 | Battery Current | int16 | 0.1 | A | Yes | Yes | Yes | Positive=charging |
| 13022 | Battery Power | int16 | 1 | W | Yes | Yes | Yes | Positive=charging (new firmware) |
| 13023 | Battery Level (SoC) | uint16 | 0.1 | % | No | Yes | Yes | State of charge |
| 13024 | Battery State of Health | uint16 | 0.1 | % | No | Yes | Yes | Remaining capacity % |
| 13025 | Battery Temperature | int16 | 0.1 | C | Yes | Yes | Yes | Battery pack temperature |
| 13026 | Daily Battery Discharge | uint16 | 0.1 | kWh | No | Yes | Yes | Today's discharge |
| 13027-13028 | Total Battery Discharge | uint32 | 0.1 | kWh | No | Yes | Yes | Lifetime discharge |

### AC Output - Hybrid (13030-13034)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 13030 | Phase A Current | int16 | 0.1 | A | Yes | Yes | Yes | All hybrid inverters |
| 13031 | Phase B Current | int16 | 0.1 | A | Yes | Yes | Yes | Three-phase only |
| 13032 | Phase C Current | int16 | 0.1 | A | Yes | Yes | Yes | Three-phase only |
| 13033-13034 | Total Active Power | int32 | 1 | W | Yes | Yes | Yes | Word swap |

### Grid Import/Export Energy (13035-13046)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 13035 | Daily Imported Energy | uint16 | 0.1 | kWh | No | Yes | Yes | From grid today |
| 13036-13037 | Total Imported Energy | uint32 | 0.1 | kWh | No | Yes | Yes | Word swap |
| 13039 | Daily Battery Charge | uint16 | 0.1 | kWh | No | Yes | Yes | Total charge today |
| 13040-13041 | Total Battery Charge | uint32 | 0.1 | kWh | No | Yes | Yes | Word swap |
| 13044 | Daily Exported Energy | uint16 | 0.1 | kWh | No | Yes | Yes | To grid today |
| 13045-13046 | Total Exported Energy | uint32 | 0.1 | kWh | No | Yes | Yes | Word swap |

### Firmware Versions (13249-13294)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 13249-13263 | Inverter Firmware Version | string(15) | - | - | No | Yes | Yes | UTF-8 string |
| 13264-13278 | Communication Module Firmware | string(15) | - | - | No | Yes | Yes | UTF-8 string |
| 13279-13293 | Battery Firmware Version | string(15) | - | - | No | Yes | Yes | UTF-8 string |

---

## Holding Registers (Read/Write)

### Inverter Control (12999)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 12999 | Inverter Start/Stop | uint16 | 1 | - | No | Yes (switch) | Yes | 0xCF=Start, 0xCE=Stop |

### Load Adjustment Mode (13001-13015) - Holding

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 13001 | Load Adjustment Mode Selection | uint16 | 1 | - | No | Yes (select) | Yes | 0=Timing, 1=ON/OFF, 2=Power opt, 3=Disabled |
| 13003 | Load Timing Period 1 Start Hour | uint16 | 1 | - | No | Yes (time) | - | Hour (0-23) |
| 13004 | Load Timing Period 1 Start Minute | uint16 | 1 | - | No | Yes (time) | - | Minute (0-59) |
| 13005 | Load Timing Period 1 End Hour | uint16 | 1 | - | No | Yes (time) | - | Hour (0-23) |
| 13006 | Load Timing Period 1 End Minute | uint16 | 1 | - | No | Yes (time) | - | Minute (0-59) |
| 13007 | Load Timing Period 2 Start Hour | uint16 | 1 | - | No | Yes (time) | - | Hour (0-23) |
| 13008 | Load Timing Period 2 Start Minute | uint16 | 1 | - | No | Yes (time) | - | Minute (0-59) |
| 13009 | Load Timing Period 2 End Hour | uint16 | 1 | - | No | Yes (time) | - | Hour (0-23) |
| 13010 | Load Adjustment On/Off | uint16 | 1 | - | No | Yes (switch) | Yes | 0xAA=On, 0x55=Off |
| 13012 | Load Power Optimized Start Hour | uint16 | 1 | - | No | Yes (time) | - | Hour (0-23) |
| 13013 | Load Power Optimized Start Minute | uint16 | 1 | - | No | Yes (time) | - | Minute (0-59) |
| 13014 | Load Power Optimized End Hour | uint16 | 1 | - | No | Yes (time) | - | Hour (0-23) |
| 13015 | Load Power Optimized End Minute | uint16 | 1 | - | No | Yes (time) | - | Minute (0-59) |

### EMS Control (13049-13052)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 13049 | EMS Mode Selection | uint16 | 1 | - | No | Yes (sensor/select) | Yes | See EMS mode values |
| 13050 | Battery Forced Charge/Discharge Cmd | uint16 | 1 | - | No | Yes (sensor/select) | Yes | 0xAA=Charge, 0xBB=Discharge, 0xCC=Stop |
| 13051 | Battery Forced Charge/Discharge Power | uint16 | 1 | W | No | Yes (sensor/number) | Yes | Target power |

### SoC Limits (13057-13058)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 13057 | Max SoC | uint16 | 0.1 | % | No | Yes | Yes | Maximum charge level |
| 13058 | Min SoC | uint16 | 0.1 | % | No | Yes | Yes | Minimum discharge level |

### Export Limits (13073-13086)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 13073 | Export Power Limit | uint16 | 1 | W | No | Yes | Yes | Feed-in limitation value |
| 13074 | Backup Mode | uint16 | 1 | - | No | Yes (sensor/switch) | Yes | 0xAA=Enable, 0x55=Disable |
| 13086 | Export Power Limit Mode | uint16 | 1 | - | No | Yes (sensor/switch) | Yes | 0xAA=Enable, 0x55=Disable |

### Reserved SoC for Backup (13099)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 13099 | Reserved SoC For Backup | uint16 | 1 | % | No | Yes | Yes | Undocumented, reverse engineered |

### Global MPP Scan (30229)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 30229 | Global MPP Scan Manual | uint16 | 1 | - | No | No | Yes | 0xAA=Enable, 0x55=Disable |

### Battery Power Settings (33046-33150)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 33046 | Battery Max Charge Power | uint16 | 10 | W | No | Yes | Yes | Maximum charging rate |
| 33047 | Battery Max Discharge Power | uint16 | 10 | W | No | Yes | Yes | Maximum discharge rate |
| 33148 | Battery Charging Start Power | uint16 | 10 | W | No | Yes | Yes | Undocumented |
| 33149 | Battery Discharging Start Power | uint16 | 10 | W | No | Yes | Yes | Undocumented |

---

## Battery Stack Registers (Slave ID 200+)

These registers are read from battery stacks directly (not via inverter). Requires direct LAN connection to inverter, not via WiNet-S.

### Battery Stack Information (10710-10720)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 10710-10719 | Battery Stack Serial Number | string(10) | - | - | No | Yes | Commented | UTF-8 string |
| 10720-10729 | Battery Stack Firmware | string(10) | - | - | No | Yes | - | UTF-8 string |

### Battery Stack Status (10740-10759)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 10740 | Battery Stack Voltage | uint16 | 0.1 | V | No | Yes | - | Stack voltage |
| 10741 | Battery Stack Current | int16 | 0.1 | A | Yes | Yes | - | Positive=charging |
| 10742 | Battery Stack Temperature | uint16 | 0.1 | C | No | Yes | - | Stack temperature |
| 10743 | Battery Stack SOC | uint16 | 0.1 | % | No | Yes | - | Higher resolution than 13023 |
| 10744 | Battery Stack SOH | uint16 | 1 | % | No | Yes | - | Stack health |
| 10745-10746 | Battery Stack Total Charge | uint32 | 0.1 | kWh | No | Yes | - | Word swap |
| 10747-10748 | Battery Stack Total Discharge | uint32 | 0.1 | kWh | No | Yes | - | Word swap |
| 10756 | Battery Stack Max Cell Voltage | uint16 | 0.0001 | V | No | Yes | - | 0.1mV resolution |
| 10757 | Battery Stack Max Cell Position | uint16 | 1 | - | No | Yes | - | Cell number |
| 10758 | Battery Stack Min Cell Voltage | uint16 | 0.0001 | V | No | Yes | - | 0.1mV resolution |
| 10759 | Battery Stack Min Cell Position | uint16 | 1 | - | No | Yes | - | Cell number |

---

## String/Grid Inverter Switch Registers (Holding)

| Register | Name | Data Type | Scale | Unit | Signed | Implemented | YAML Example | Notes |
|----------|------|-----------|-------|------|--------|-------------|--------------|-------|
| 5007 | Power Limitation Switch | uint16 | 1 | - | No | Yes (switch) | - | 0xAA=Enable, 0x55=Disable |
| 5010 | Export Power Limitation | uint16 | 1 | - | No | Yes (switch) | - | 0xAA=Enable, 0x55=Disable |

---

## Missing Registers (In YAML but NOT Implemented)

| Register | Name | Data Type | Unit | Notes |
|----------|------|-----------|------|-------|
| 5002 (5003 comment) | Daily PV generation & battery discharge | uint16 | kWh | YAML combines PV+battery in early register |
| 5003-5004 | Total PV generation & battery discharge | uint32 | kWh | YAML version at earlier address |
| 6226-6237 | Monthly PV Generation | uint16 | kWh | LAN-only, not implemented |
| 6257-6277 | Yearly PV Generation | uint32 | kWh | LAN-only, not implemented |
| 6595-6606 | Monthly Export | uint16 | kWh | LAN-only, not implemented |
| 6615-6634 | Yearly Export | uint32 | kWh | LAN-only, not implemented |
| 30229 | Global MPP Scan Manual | uint16 | - | Not implemented |

---

## Value Mappings

### System State (Register 12999)

| Value | State |
|-------|-------|
| 0x0000, 0x0040 | Running |
| 0x0001, 0x8000 | Stop |
| 0x0002, 0x1300 | Shutdown |
| 0x0004, 0x1500 | Emergency Stop |
| 0x0008, 0x1400 | Standby |
| 0x0010, 0x1200 | Initial Standby |
| 0x0020, 0x1600 | Startup |
| 0x0040 | Running |
| 0x0080, 0x8100 | De-rating Running |
| 0x0100, 0x5500 | Fault |
| 0x0200 | Update Failed |
| 0x0400 | Maintain Mode |
| 0x0410 | Off-grid Charge |
| 0x0800 | Forced Mode |
| 0x1000 | Off-grid Mode |
| 0x1111 | Un-Initialized |
| 0x1700 | AFCI Self Test Shutdown |
| 0x1800 | Intelligent Station Building Status |
| 0x1900 | Safe Mode |
| 0x2000 | Open Loop |
| 0x2501 | Restarting |
| 0x4000 | External EMS Mode |
| 0x4001 | Emergency Battery Charging |
| 0x8200 | Dispatch Run |
| 0x9100 | Warn Running |

### Running State (Register 13000) - Bit Field

| Bit | Meaning |
|-----|---------|
| 0x01 | PV Generating |
| 0x02 | Battery Charging |
| 0x04 | Battery Discharging |
| 0x10 | Exporting Power |
| 0x20 | Importing Power |

### EMS Mode Selection (Register 13049)

| Value | Mode |
|-------|------|
| 0 | Self-consumption mode (default) |
| 2 | Forced mode (compulsory mode) |
| 3 | External EMS |
| 4 | VPP (Virtual Power Plant) |
| 8 | MicroGrid |

### Battery Forced Charge/Discharge Command (Register 13050)

| Value | Command |
|-------|---------|
| 0xAA (170) | Forced Charge |
| 0xBB (187) | Forced Discharge |
| 0xCC (204) | Stop (default) |

### Backup Mode / Export Limit Mode (Registers 13074, 13086)

| Value | State |
|-------|-------|
| 0xAA (170) | Enabled |
| 0x55 (85) | Disabled |

### Load Adjustment On/Off (Register 13010)

| Value | State |
|-------|-------|
| 0xAA (170) | ON |
| 0x55 (85) | OFF |

### Load Adjustment Mode (Register 13001)

| Value | Mode |
|-------|------|
| 0 | Timing |
| 1 | ON/OFF |
| 2 | Power optimization |
| 3 | Disabled |

### Inverter Start/Stop (Register 12999 - Holding)

| Value | Command |
|-------|---------|
| 0xCF (207) | Start |
| 0xCE (206) | Stop |

---

## Data Validation Reference

| Data Type | Range | Notes |
|-----------|-------|-------|
| uint16 | 0 to 65535 | Unsigned 16-bit integer |
| int16 | -32768 to 32767 | Signed 16-bit integer |
| uint32 | 0 to 4294967295 | Unsigned 32-bit integer (word swap) |
| int32 | -2147483648 to 2147483647 | Signed 32-bit integer (word swap) |
| string | - | Multiple consecutive registers as UTF-8 |

### Common Scale Factors

| Scale | Calculation | Example |
|-------|-------------|---------|
| 0.1 | raw_value * 0.1 | 2345 -> 234.5 |
| 0.01 | raw_value * 0.01 | 5012 -> 50.12 |
| 0.001 | raw_value * 0.001 | 1000 -> 1.000 |
| 0.0001 | raw_value * 0.0001 | 33450 -> 3.345V |
| 10 | raw_value * 10 | 500 -> 5000W |
| 100 | raw_value * 100 | 50 -> 5000W |

### 32-bit Word Swap

Sungrow uses word swap for 32-bit values:
- Register N contains HIGH word (bits 31-16)
- Register N+1 contains LOW word (bits 15-0)
- Value = (reg_N << 16) | reg_N+1

### Signed Integer Handling

For signed values (int16, int32):
- Values >= 0x8000 (uint16) or >= 0x80000000 (uint32) are negative
- Convert: if value >= 0x8000: value = value - 0x10000
- Example: 0xFFFF (65535 unsigned) = -1 (signed)

---

## References

- Sungrow Communication Protocol of Residential Hybrid Inverter V1.1.5 (TI_20240924)
- [mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant)
- [photovoltaikforum.com Sungrow Modbus thread](https://www.photovoltaikforum.com/thread/166134-daten-lesen-vom-sungrow-wechselrichtern-modbus/)
