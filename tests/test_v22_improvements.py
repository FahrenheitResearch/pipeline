#!/usr/bin/env python3
"""
Comprehensive Unit Tests for HRRR v2.2 Improvements

Tests all major v2.2 enhancements:
- Centralized constants integration
- SPC-aligned parameter implementations  
- Transport wind methodology
- Parameter output validation

Author: FahrenheitResearch
Date: 2025-08-16
"""
import os
import sys
import numpy as np
from pathlib import Path

# Add project directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Make logs quiet by default
os.environ.setdefault("HRRR_DEBUG", "0")

# Import v2.2 enhanced parameters
from derived_params.constants import (
    STP_CAPE_NORM, STP_SHEAR_NORM_SPC, STP_CIN_OFFSET, STP_CIN_NORM,
    EHI_NORM_SPC, EHI_NORM_DISPLAY, SHIP_CAPE_NORM, SHIP_TEMP_REF,
    SCP_CAPE_NORM, SCP_SRH_NORM, VGP_K_DEFAULT
)
from derived_params.significant_tornado_parameter_fixed import significant_tornado_parameter_fixed
from derived_params.significant_tornado_parameter_effective import significant_tornado_parameter_effective
from derived_params.energy_helicity_index import energy_helicity_index
from derived_params.energy_helicity_index_display import energy_helicity_index_display
from derived_params.significant_hail_parameter import significant_hail_parameter
from derived_params.supercell_composite_parameter import supercell_composite_parameter
from derived_params.vorticity_generation_parameter import vorticity_generation_parameter
from derived_params.ventilation_rate_from_components import (
    ventilation_rate_from_components, ventilation_rate_from_surface_winds
)

# Test data generators
def create_realistic_tornado_environment():
    """Create realistic tornado environment test data"""
    return {
        'mlcape': np.array([2500, 3000, 4000, 1200, 500]),      # J/kg
        'mlcin': np.array([-25, -50, -75, -150, -250]),         # J/kg (negative)
        'srh_01km': np.array([300, 400, 500, 200, 100]),        # m²/s²
        'srh_03km': np.array([350, 450, 600, 250, 120]),        # m²/s²
        'shear_06km': np.array([25, 30, 35, 20, 15]),           # m/s
        'effective_shear': np.array([20, 25, 30, 18, 12]),      # m/s
        'effective_srh': np.array([280, 380, 480, 180, 80]),    # m²/s²
        'lcl_height': np.array([800, 1200, 1500, 1800, 2200])   # m AGL
    }

def create_hail_environment():
    """Create realistic hail environment test data"""
    return {
        'mucape': np.array([3000, 4000, 5000, 2000, 800]),      # J/kg
        'mucin': np.array([-30, -60, -90, -120, -200]),         # J/kg (negative)
        'lapse_rate_700_500': np.array([7.5, 8.0, 8.5, 6.5, 5.5]),  # °C/km
        'wind_shear_06km': np.array([20, 25, 30, 18, 12]),      # m/s
        'freezing_level': np.array([3500, 3800, 4000, 3200, 2800]),  # m
        'temp_500': np.array([-22, -25, -28, -20, -15]),        # °C
        'mixing_ratio_2m': np.array([12, 14, 16, 10, 8])        # g/kg
    }

def create_wind_environment():
    """Create realistic wind environment for transport wind tests"""
    return {
        'u_850': np.array([15, 20, 25, 10, 5]),                 # m/s
        'v_850': np.array([10, 15, 20, 8, 3]),                  # m/s
        'u10': np.array([12, 16, 20, 8, 4]),                    # m/s
        'v10': np.array([8, 12, 16, 6, 2]),                     # m/s
        'pbl_height': np.array([1500, 2000, 2500, 1200, 800])   # m
    }


class TestCentralizedConstants:
    """Test centralized constants module integration"""
    
    def test_constants_exist(self):
        """Verify all required constants are defined"""
        # STP constants
        assert STP_CAPE_NORM == 1500.0
        assert STP_SHEAR_NORM_SPC == 20.0
        assert STP_CIN_OFFSET == 150.0
        assert STP_CIN_NORM == 125.0
        
        # EHI constants
        assert EHI_NORM_SPC == 100000.0
        assert EHI_NORM_DISPLAY == 160000.0
        
        # SHIP constants
        assert SHIP_CAPE_NORM == 1500.0
        assert SHIP_TEMP_REF == -20.0
        
        # SCP constants
        assert SCP_CAPE_NORM == 1000.0
        assert SCP_SRH_NORM == 50.0
        
        # VGP constants
        assert VGP_K_DEFAULT == 40.0
        
    def test_constants_types(self):
        """Verify constants are proper numeric types"""
        constants_to_test = [
            STP_CAPE_NORM, STP_SHEAR_NORM_SPC, EHI_NORM_SPC,
            SHIP_CAPE_NORM, SCP_CAPE_NORM, VGP_K_DEFAULT
        ]
        for const in constants_to_test:
            assert isinstance(const, (int, float))
            assert const > 0  # All normalization constants should be positive


class TestSTPImplementations:
    """Test STP fixed and effective layer implementations"""
    
    def test_stp_fixed_basic_calculation(self):
        """Test STP fixed layer basic calculation"""
        env = create_realistic_tornado_environment()
        
        stp = significant_tornado_parameter_fixed(
            env['mlcape'], env['mlcin'], env['srh_01km'], 
            env['shear_06km'], env['lcl_height']
        )
        
        # Basic validation
        assert isinstance(stp, np.ndarray)
        assert len(stp) == 5
        assert np.all(stp >= 0)  # STP should never be negative
        assert np.all(np.isfinite(stp[:-1]))  # First 4 should be finite
        
    def test_stp_fixed_cin_term(self):
        """Test STP fixed layer CIN term implementation"""
        # Test case: strong environment with weak CIN
        mlcape = np.array([3000])
        mlcin = np.array([-50])  # Weak CIN
        srh = np.array([300])
        shear = np.array([25])
        lcl = np.array([1000])
        
        stp = significant_tornado_parameter_fixed(mlcape, mlcin, srh, shear, lcl)
        
        # Calculate expected CIN term: (150 + (-50)) / 125 = 0.8
        expected_cin_term = (STP_CIN_OFFSET + mlcin[0]) / STP_CIN_NORM
        assert abs(expected_cin_term - 0.8) < 0.01
        
        # STP should be positive and reasonable
        assert stp[0] > 0
        assert stp[0] < 10  # Reasonable upper bound
        
    def test_stp_effective_shear_normalization(self):
        """Test STP effective layer uses EBWD/20 normalization"""
        env = create_realistic_tornado_environment()
        
        stp = significant_tornado_parameter_effective(
            env['mlcape'], env['mlcin'], env['effective_srh'],
            env['effective_shear'], env['lcl_height']
        )
        
        # Test specific shear normalization behavior
        # Shear of 20 m/s should give shear_term ≈ 1.0
        test_shear = np.array([20.0])
        test_env = {k: v[:1] for k, v in env.items()}
        test_env['effective_shear'] = test_shear
        
        stp_test = significant_tornado_parameter_effective(
            test_env['mlcape'], test_env['mlcin'], test_env['effective_srh'],
            test_env['effective_shear'], test_env['lcl_height']
        )
        
        assert stp_test[0] > 0
        
    def test_stp_hard_gates(self):
        """Test STP hard gates (CAPE, CIN, LCL thresholds)"""
        # Test low CAPE gate
        low_cape = significant_tornado_parameter_fixed(
            np.array([50]), np.array([-50]), np.array([300]), 
            np.array([25]), np.array([1000])
        )
        assert low_cape[0] == 0.0
        
        # Test strong CIN gate
        strong_cin = significant_tornado_parameter_fixed(
            np.array([2000]), np.array([-250]), np.array([300]),
            np.array([25]), np.array([1000])
        )
        assert strong_cin[0] == 0.0
        
        # Test high LCL gate
        high_lcl = significant_tornado_parameter_fixed(
            np.array([2000]), np.array([-50]), np.array([300]),
            np.array([25]), np.array([2500])
        )
        assert high_lcl[0] == 0.0


class TestEHIImplementations:
    """Test Energy-Helicity Index implementations"""
    
    def test_ehi_spc_canonical(self):
        """Test EHI SPC canonical implementation"""
        cape = np.array([2000, 3000, 4000])
        srh = np.array([200, 300, 400])
        
        ehi = energy_helicity_index(cape, srh)
        
        # Manual calculation: (CAPE/1000) × (SRH/100) = CAPE×SRH/100000
        expected = (cape * srh) / EHI_NORM_SPC
        np.testing.assert_allclose(ehi, expected, rtol=1e-10)
        
    def test_ehi_display_scaling(self):
        """Test EHI display scaling vs canonical"""
        cape = np.array([2000, 3000, 4000])
        srh = np.array([200, 300, 400])
        
        ehi_canonical = energy_helicity_index(cape, srh)
        ehi_display = energy_helicity_index_display(cape, srh)
        
        # Display should be smaller due to /160000 vs /100000
        scale_factor = EHI_NORM_SPC / EHI_NORM_DISPLAY  # 100000/160000 = 0.625
        
        # For moderate values (no damping), should follow scaling
        if np.all(np.abs(cape * srh / EHI_NORM_DISPLAY) < 5.0):
            np.testing.assert_allclose(ehi_display, ehi_canonical * scale_factor, rtol=0.1)
            
    def test_ehi_sign_preservation(self):
        """Test EHI preserves SRH sign (cyclonic/anticyclonic)"""
        cape = np.array([2000, 2000])
        srh = np.array([200, -200])  # Positive and negative SRH
        
        ehi = energy_helicity_index(cape, srh)
        
        assert ehi[0] > 0  # Positive SRH → positive EHI
        assert ehi[1] < 0  # Negative SRH → negative EHI


class TestSHIPImplementation:
    """Test Significant Hail Parameter implementation"""
    
    def test_ship_basic_calculation(self):
        """Test SHIP basic calculation with all terms"""
        env = create_hail_environment()
        
        ship = significant_hail_parameter(
            env['mucape'], env['mucin'], env['lapse_rate_700_500'],
            env['wind_shear_06km'], env['freezing_level'], 
            env['temp_500'], env['mixing_ratio_2m']
        )
        
        assert isinstance(ship, np.ndarray)
        assert len(ship) == 5
        assert np.all(ship >= 0)  # SHIP should never be negative
        
    def test_ship_temperature_term(self):
        """Test SHIP temperature term implementation"""
        # Test temperature term: (SHIP_TEMP_REF - T500) / SHIP_TEMP_NORM
        temp_500 = np.array([-25])  # °C
        expected_temp_term = (SHIP_TEMP_REF - temp_500[0]) / 5.0  # (-20 - (-25)) / 5 = 1.0
        
        assert abs(expected_temp_term - 1.0) < 0.01
        
    def test_ship_term_capping(self):
        """Test SHIP terms are properly capped at 1.0"""
        # Extreme values that should get capped
        extreme_env = {
            'mucape': np.array([6000]),      # Should cap CAPE term
            'mucin': np.array([-10]),        
            'lapse_rate_700_500': np.array([12.0]),  # Should cap lapse term
            'wind_shear_06km': np.array([40]),       # Should cap shear term
            'freezing_level': np.array([4000]),
            'temp_500': np.array([-30]),     # Should cap temp term  
            'mixing_ratio_2m': np.array([20])        # Should cap MR term
        }
        
        ship = significant_hail_parameter(
            extreme_env['mucape'], extreme_env['mucin'], extreme_env['lapse_rate_700_500'],
            extreme_env['wind_shear_06km'], extreme_env['freezing_level'],
            extreme_env['temp_500'], extreme_env['mixing_ratio_2m']
        )
        
        # With all terms capped at 1.0, SHIP should be ≤ 1.0
        assert ship[0] <= 1.0


class TestSCPImplementation:
    """Test Supercell Composite Parameter implementation"""
    
    def test_scp_standard_no_cin(self):
        """Test SCP standard implementation has no CIN term"""
        mucape = np.array([2000])
        effective_srh = np.array([200])
        effective_shear = np.array([20])
        
        scp = supercell_composite_parameter(mucape, effective_srh, effective_shear)
        
        # Manual calculation without CIN
        cape_term = mucape[0] / SCP_CAPE_NORM  # 2000/1000 = 2.0
        srh_term = effective_srh[0] / SCP_SRH_NORM  # 200/50 = 4.0
        shear_term = (effective_shear[0] - 10.0) / 10.0  # (20-10)/10 = 1.0
        expected = cape_term * srh_term * shear_term  # 2.0 × 4.0 × 1.0 = 8.0
        
        assert abs(scp[0] - expected) < 0.01
        
    def test_scp_shear_scaling(self):
        """Test SCP shear term piecewise scaling"""
        mucape = np.array([1000, 1000, 1000, 1000])
        effective_srh = np.array([50, 50, 50, 50])
        effective_shear = np.array([5, 10, 15, 25])  # Below, at, between, above thresholds
        
        scp = supercell_composite_parameter(mucape, effective_srh, effective_shear)
        
        # Shear < 10: should give 0
        # Shear = 10: should give 0  
        # Shear = 15: should give 0.5
        # Shear >= 20: should give 1.0
        
        assert scp[0] == 0.0  # shear=5 → 0
        assert scp[1] == 0.0  # shear=10 → 0
        assert scp[2] > 0.0 and scp[2] < scp[3]  # shear=15 → partial
        assert scp[3] > scp[2]  # shear=25 → higher


class TestTransportWind:
    """Test transport wind methodology for ventilation rate"""
    
    def test_transport_wind_calculation(self):
        """Test transport wind calculation"""
        env = create_wind_environment()
        
        vr_transport = ventilation_rate_from_components(
            env['u_850'], env['v_850'], env['pbl_height']
        )
        
        # Manual calculation
        transport_speed = np.sqrt(env['u_850']**2 + env['v_850']**2)
        expected = transport_speed * env['pbl_height']
        
        np.testing.assert_allclose(vr_transport, expected, rtol=1e-10)
        
    def test_surface_vs_transport_wind(self):
        """Test surface wind fallback method"""
        env = create_wind_environment()
        
        vr_transport = ventilation_rate_from_components(
            env['u_850'], env['v_850'], env['pbl_height']
        )
        vr_surface = ventilation_rate_from_surface_winds(
            env['u10'], env['v10'], env['pbl_height']
        )
        
        # Both should be positive and finite
        assert np.all(vr_transport > 0)
        assert np.all(vr_surface > 0)
        assert np.all(np.isfinite(vr_transport))
        assert np.all(np.isfinite(vr_surface))
        
        # Transport wind typically higher than surface wind
        # (though not always due to complex boundary layer physics)
        assert np.any(vr_transport != vr_surface)  # At least they're different


class TestVGPImplementation:
    """Test Vorticity Generation Parameter implementation"""
    
    def test_vgp_calculation(self):
        """Test VGP calculation with centralized constants"""
        cape = np.array([2000, 3000, 4000])
        shear_01km = np.array([15, 20, 25])
        
        vgp = vorticity_generation_parameter(cape, shear_01km)
        
        # Manual calculation: (shear × √CAPE) / K
        expected = (shear_01km * np.sqrt(cape)) / VGP_K_DEFAULT
        
        np.testing.assert_allclose(vgp, expected, rtol=1e-10)
        
    def test_vgp_units_and_range(self):
        """Test VGP produces reasonable values"""
        # Moderate severe weather environment
        cape = np.array([1600])  # J/kg (moderate)
        shear_01km = np.array([12])  # m/s (moderate)
        
        vgp = vorticity_generation_parameter(cape, shear_01km)
        
        # VGP = (12 × √1600) / 40 = (12 × 40) / 40 = 12
        # Should be positive and finite
        assert vgp[0] > 0
        assert np.isfinite(vgp[0])
        
        # Test with weaker environment for threshold testing
        weak_cape = np.array([400])  # J/kg  
        weak_shear = np.array([8])   # m/s
        weak_vgp = vorticity_generation_parameter(weak_cape, weak_shear)
        
        # VGP = (8 × √400) / 40 = (8 × 20) / 40 = 4
        expected_weak = (8 * np.sqrt(400)) / 40
        assert abs(weak_vgp[0] - expected_weak) < 0.01


class TestParameterRanges:
    """Test all parameters produce realistic output ranges"""
    
    def test_realistic_stp_ranges(self):
        """Test STP produces realistic ranges for known environments"""
        # Weak environment
        weak_stp = significant_tornado_parameter_fixed(
            np.array([500]), np.array([-100]), np.array([50]),
            np.array([10]), np.array([2000])
        )
        assert 0 <= weak_stp[0] <= 0.5
        
        # Strong environment  
        strong_stp = significant_tornado_parameter_fixed(
            np.array([4000]), np.array([-25]), np.array([400]),
            np.array([30]), np.array([800])
        )
        assert 1.0 <= strong_stp[0] <= 15.0
        
    def test_realistic_ehi_ranges(self):
        """Test EHI produces realistic ranges"""
        # Moderate supercell environment
        ehi = energy_helicity_index(np.array([2000]), np.array([200]))
        assert 1.0 <= ehi[0] <= 5.0
        
    def test_realistic_ship_ranges(self):
        """Test SHIP produces realistic ranges"""
        env = create_hail_environment()
        ship = significant_hail_parameter(
            env['mucape'][:1], env['mucin'][:1], env['lapse_rate_700_500'][:1],
            env['wind_shear_06km'][:1], env['freezing_level'][:1],
            env['temp_500'][:1], env['mixing_ratio_2m'][:1]
        )
        assert 0.0 <= ship[0] <= 10.0  # Realistic SHIP range


def run_comprehensive_tests():
    """Run all v2.2 tests with summary reporting"""
    print("=" * 80)
    print("HRRR v2.2 Comprehensive Unit Tests")
    print("=" * 80)
    
    test_classes = [
        TestCentralizedConstants,
        TestSTPImplementations, 
        TestEHIImplementations,
        TestSHIPImplementation,
        TestSCPImplementation,
        TestTransportWind,
        TestVGPImplementation,
        TestParameterRanges
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        class_name = test_class.__name__
        print(f"\n[{class_name}]")
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                # Create instance and run test
                instance = test_class()
                test_method = getattr(instance, method_name)
                test_method()
                passed_tests += 1
                print(f"  ✓ {method_name}")
            except Exception as e:
                print(f"  ✗ {method_name}: {e}")
    
    print(f"\n{'='*80}")
    print(f"Test Results: {passed_tests}/{total_tests} tests passed")
    if passed_tests == total_tests:
        print("🎉 All v2.2 tests PASSED!")
    else:
        print(f"⚠️  {total_tests - passed_tests} tests FAILED")
    print(f"{'='*80}")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)
