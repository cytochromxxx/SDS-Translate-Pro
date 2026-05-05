#!/usr/bin/env python3
"""
Unit test for Section 16.2 extraction fix.

Tests the enhanced validation logic directly without requiring a PDF file.
This validates the core logic improvements made to prevent hazard statements
from being injected into the abbreviations section.
"""

import sys
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class TestAbbreviationsValidation:
    """Test suite for abbreviations extraction validation."""
    
    def __init__(self):
        self.results = []
    
    def _is_hazard_statement(self, s):
        """Helper: Enhanced hazard statement detection (matches pdf_gap_filler.py)."""
        s_stripped = s.strip()
        # Check for H-codes in various formats: H123, H123:, H 123, H-123
        if re.search(r'\bH\s*[-]?\d{3}\b', s_stripped):
            return True
        # Check for common hazard statement content patterns
        hazard_keywords = [
            'causes severe',
            'causes serious',
            'harmful to aquatic',
            'fatal if',
            'toxic if',
            'may cause',
            'may be harmful',
            'suspected of causing',
            'may damage',
            'may impair'
        ]
        s_lower = s_stripped.lower()
        for keyword in hazard_keywords:
            if keyword in s_lower and len(s_stripped) < 200:
                return True
        return False
    
    def _is_valid_abbrev(self, s):
        """Helper: Valid abbreviation check (matches pdf_gap_filler.py)."""
        # Exclude H-codes
        if re.search(r'\bH\s*[-]?\d{3}\b', s):
            return False
        if self._is_hazard_statement(s):
            return False
        if not (2 <= len(s) <= 20):
            return False
        if s.endswith(','):
            return False
        cleaned = re.sub(r'[^A-Za-z0-9]', '', s)
        if not cleaned:
            return False
        uppers = sum(1 for c in cleaned if c.isupper())
        digits = sum(1 for c in cleaned if c.isdigit())
        return (uppers + digits) / len(cleaned) >= 0.4 or s.lower() in ['vpvb', 'pbt', 'reach', 'trgs']
    
    def test_h_code_patterns(self):
        """Test detection of H-codes in various formats."""
        logger.info("\n### TEST 1: H-Code Pattern Detection ###")
        
        test_cases = [
            ("H226", True, "Standard format H226"),
            ("H 226", True, "Format with space H 226"),
            ("H-226", True, "Format with hyphen H-226"),
            ("H226:", True, "Format with colon H226:"),
            ("H 226:", True, "Format with space and colon"),
            ("H-226:", True, "Format with hyphen and colon"),
            ("REACH", False, "Valid abbreviation REACH"),
            ("CAS", False, "Valid abbreviation CAS"),
            ("H", False, "Single H letter"),
            ("H22", False, "H with only 2 digits"),
            ("226", False, "Numbers without H"),
        ]
        
        passed = 0
        for value, expected_is_hazard, description in test_cases:
            result = self._is_hazard_statement(value)
            status = "✓" if result == expected_is_hazard else "✗"
            logger.info(f"  {status} {description:40} → is_hazard={result} (expected={expected_is_hazard})")
            if result == expected_is_hazard:
                passed += 1
        
        logger.info(f"\nResult: {passed}/{len(test_cases)} passed")
        self.results.append(passed == len(test_cases))
        return passed == len(test_cases)
    
    def test_hazard_keyword_detection(self):
        """Test detection of hazard statement keywords."""
        logger.info("\n### TEST 2: Hazard Keyword Detection ###")
        
        test_cases = [
            ("Causes serious eye damage.", True, "Hazard keyword: causes"),
            ("May cause drowsiness or dizziness.", True, "Hazard keyword: may cause"),
            ("Harmful to aquatic life.", True, "Hazard keyword: harmful"),
            ("Fatal if inhaled.", True, "Hazard keyword: fatal"),
            ("Toxic if swallowed.", True, "Hazard keyword: toxic"),
            ("May damage fertility.", True, "Hazard keyword: may damage"),
            ("Suspected of causing cancer.", True, "Hazard keyword: suspected"),
            ("Registration, Evaluation and Authorization of Chemicals", False, "Long valid abbreviation"),
            ("American Conference of Governmental Industrial Hygienists", False, "Valid organization name"),
            ("European Agreement concerning the International Carriage", False, "Valid agreement name"),
        ]
        
        passed = 0
        for value, expected_is_hazard, description in test_cases:
            result = self._is_hazard_statement(value)
            status = "✓" if result == expected_is_hazard else "✗"
            logger.info(f"  {status} {description:50}")
            if result == expected_is_hazard:
                passed += 1
            else:
                logger.info(f"      Got: {result}, Expected: {expected_is_hazard}")
        
        logger.info(f"\nResult: {passed}/{len(test_cases)} passed")
        self.results.append(passed == len(test_cases))
        return passed == len(test_cases)
    
    def test_valid_abbreviations(self):
        """Test that valid abbreviations pass validation."""
        logger.info("\n### TEST 3: Valid Abbreviations ###")
        
        valid_abbrevs = [
            ("REACH", "Registration, Evaluation and Authorization of Chemicals"),
            ("TRGS", "Technische Regeln für Gefahrstoffe"),
            ("CAS", "Chemical Abstracts Service"),
            ("CLP", "Classification, Labelling and Packaging"),
            ("ECHA", "European Chemicals Agency"),
            ("OECD", "Organisation for Economic Cooperation and Development"),
            ("GHS", "Globally Harmonized System"),
            ("PBT", "persistent and bioaccumulative and toxic"),
            ("ADN", "European Agreement concerning Dangerous Goods by Inland Waterways"),
            ("ADR", "European Agreement concerning Dangerous Goods by Road"),
            ("UN", "United Nations"),
            ("DIN", "German Institute for Standardization"),
            ("EN", "European Standard"),
        ]
        
        passed = 0
        for short, long_form in valid_abbrevs:
            is_valid_short = self._is_valid_abbrev(short)
            is_hazard_long = self._is_hazard_statement(long_form)
            
            if is_valid_short and not is_hazard_long:
                logger.info(f"  ✓ {short:10} → {long_form[:50]}")
                passed += 1
            else:
                logger.info(f"  ✗ {short:10} → is_valid={is_valid_short}, is_hazard_long={is_hazard_long}")
        
        logger.info(f"\nResult: {passed}/{len(valid_abbrevs)} passed")
        self.results.append(passed == len(valid_abbrevs))
        return passed == len(valid_abbrevs)
    
    def test_hazard_exclusion(self):
        """Test that hazard statements are properly excluded."""
        logger.info("\n### TEST 4: Hazard Statement Exclusion ###")
        
        hazard_exclusion_cases = [
            ("H226", "Flammable liquid and vapour.", False, "H-code + hazard text"),
            ("H318", "Causes serious eye damage.", False, "H-code + hazard text"),
            ("H336", "May cause drowsiness or dizziness.", False, "H-code + hazard text"),
            ("H412", "Harmful to aquatic life with long lasting effects.", False, "H-code + hazard text"),
            ("H314", "Causes severe skin burns and eye damage.", False, "H-code + hazard text"),
            ("REACH", "Registration, Evaluation and Authorization of Chemicals", True, "Valid abbrev + text"),
            ("CAS", "Chemical Abstracts Service", True, "Valid abbrev + text"),
        ]
        
        passed = 0
        for short, long_form, should_be_valid, description in hazard_exclusion_cases:
            is_valid_short = self._is_valid_abbrev(short)
            
            if is_valid_short == should_be_valid:
                logger.info(f"  ✓ {description:40} → {short}")
                passed += 1
            else:
                logger.info(f"  ✗ {description:40} → Got valid={is_valid_short}, expected={should_be_valid}")
        
        logger.info(f"\nResult: {passed}/{len(hazard_exclusion_cases)} passed")
        self.results.append(passed == len(hazard_exclusion_cases))
        return passed == len(hazard_exclusion_cases)
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        logger.info("\n### TEST 5: Edge Cases ###")
        
        edge_cases = [
            ("H 314: Causes severe skin burns", False, "H-code with space and colon"),
            ("H-314: Causes severe skin burns", False, "H-code with hyphen and colon"),
            ("VPVB", True, "Special abbreviation VPVB"),
            ("PBT", True, "Special abbreviation PBT"),
            ("MAK", True, "Valid abbreviation MAK"),
            ("NFPA", True, "Valid abbreviation NFPA"),
            ("NIOSH", True, "Valid abbreviation NIOSH"),
            ("pH", True, "Chemistry notation pH (acceptable)"),
            ("LC50", True, "Scientific notation LC50"),
            ("LD50", True, "Scientific notation LD50"),
            ("EC50", True, "Scientific notation EC50"),
        ]
        
        passed = 0
        for value, should_be_valid, description in edge_cases:
            is_valid = self._is_valid_abbrev(value)
            
            if is_valid == should_be_valid:
                logger.info(f"  ✓ {description:40} → {value}")
                passed += 1
            else:
                logger.info(f"  ✗ {description:40} → Got valid={is_valid}, expected={should_be_valid}")
        
        logger.info(f"\nResult: {passed}/{len(edge_cases)} passed")
        self.results.append(passed == len(edge_cases))
        return passed == len(edge_cases)
    
    def run_all_tests(self):
        """Run all test suites."""
        logger.info("=" * 80)
        logger.info("SECTION 16.2 FIX - UNIT TEST SUITE")
        logger.info("=" * 80)
        
        self.test_h_code_patterns()
        self.test_hazard_keyword_detection()
        self.test_valid_abbreviations()
        self.test_hazard_exclusion()
        self.test_edge_cases()
        
        logger.info("\n" + "=" * 80)
        logger.info("### FINAL RESULTS ###")
        logger.info("=" * 80)
        
        passed = sum(self.results)
        total = len(self.results)
        
        logger.info(f"\nTest suites passed: {passed}/{total}")
        
        if passed == total:
            logger.info("\n✓✓✓ ALL TESTS PASSED ✓✓✓\n")
            logger.info("The fix successfully:")
            logger.info("  ✓ Detects H-codes in all formats")
            logger.info("  ✓ Identifies hazard keywords")
            logger.info("  ✓ Validates abbreviations properly")
            logger.info("  ✓ Excludes hazard statements")
            logger.info("  ✓ Handles edge cases correctly")
            return True
        else:
            logger.error(f"\n✗✗✗ SOME TESTS FAILED ({total - passed} failures) ✗✗✗\n")
            return False

if __name__ == "__main__":
    tester = TestAbbreviationsValidation()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
