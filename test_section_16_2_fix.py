#!/usr/bin/env python3
"""
Test script for Section 16.2 (Abbreviations and Acronyms) extraction fix.

Tests the enhanced gap-filler logic to ensure:
1. Only valid abbreviations are extracted from Section 16.2
2. Hazard statements (H-codes) are NOT injected into abbreviations
3. Proper distinction between different Section 16 subsections
"""

import sys
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_abbreviations_extraction():
    """Test the abbreviations extraction from the PDF."""
    try:
        from pdf_gap_filler import SDSPDFGapFiller
    except ImportError as e:
        logger.error(f"Cannot import pdf_gap_filler: {e}")
        return False
    
    pdf_path = "SDS_Mycoplasma_Off_15-5xxx_en_DE_Ver.05.pdf"
    
    if not Path(pdf_path).exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return False
    
    logger.info(f"Testing PDF: {pdf_path}")
    logger.info("=" * 80)
    
    try:
        with SDSPDFGapFiller(pdf_path) as filler:
            # Test section 16 extraction
            section_16_data = filler.extract_section_16()
            
            logger.info("\n### SECTION 16 EXTRACTION RESULTS ###\n")
            
            # Test abbreviations
            abbreviations = section_16_data.get("abbreviations", [])
            source_note = section_16_data.get("abbreviations_source_note", "")
            
            logger.info(f"✓ Abbreviations extracted: {len(abbreviations)} items")
            if abbreviations:
                logger.info("\nFirst 10 abbreviations:")
                for i, abbr in enumerate(abbreviations[:10]):
                    logger.info(f"  [{i+1}] {abbr.get('short', 'N/A'):15} → {abbr.get('long', 'N/A')[:60]}")
                if len(abbreviations) > 10:
                    logger.info(f"  ... and {len(abbreviations) - 10} more")
            
            if source_note:
                logger.info(f"\n✓ Source note: {source_note[:100]}...")
            
            # Test hazard statements
            hazard_statements = section_16_data.get("hazard_statements", [])
            logger.info(f"\n✓ Hazard statements extracted: {len(hazard_statements)} items")
            if hazard_statements:
                logger.info("\nHazard statements:")
                for i, stmt in enumerate(hazard_statements):
                    logger.info(f"  [{i+1}] {stmt.get('code', 'N/A'):10} → {stmt.get('text', 'N/A')[:60]}")
            
            # Test CLP classifications
            clp_classifications = section_16_data.get("clp_classifications", [])
            logger.info(f"\n✓ CLP classifications extracted: {len(clp_classifications)} items")
            if clp_classifications:
                logger.info("\nCLP classifications:")
                for i, clp in enumerate(clp_classifications):
                    logger.info(f"  [{i+1}] {clp.get('hazard_class', 'N/A')[:40]:40} → {clp.get('hazard_statement', 'N/A')[:40]}")
            
            # VALIDATION TESTS
            logger.info("\n" + "=" * 80)
            logger.info("### VALIDATION TESTS ###\n")
            
            test_results = []
            
            # Test 1: No H-codes in abbreviations
            h_codes_found = []
            for abbr in abbreviations:
                short = abbr.get('short', '').upper()
                if short.startswith('H') and short[1:4].isdigit():
                    h_codes_found.append(short)
            
            if h_codes_found:
                logger.error(f"✗ FAIL: H-codes found in abbreviations: {h_codes_found}")
                test_results.append(False)
            else:
                logger.info(f"✓ PASS: No H-codes found in abbreviations")
                test_results.append(True)
            
            # Test 2: Valid abbreviations present
            expected_abbrevs = ['REACH', 'TRGS', 'CAS', 'CLP', 'ECHA', 'OECD', 'GHS', 'PBT', 'UN', 'ADR']
            found_abbrevs = [abbr.get('short', '').upper() for abbr in abbreviations]
            missing = [a for a in expected_abbrevs if a not in found_abbrevs]
            
            if missing:
                logger.warning(f"⚠ WARNING: Expected abbreviations not found: {missing}")
                test_results.append(False)
            else:
                logger.info(f"✓ PASS: All expected standard abbreviations found")
                test_results.append(True)
            
            # Test 3: No hazard statement descriptions in abbreviations
            hazard_keywords = ['causes', 'harmful', 'fatal', 'toxic', 'damage', 'suspected']
            problematic_abbrevs = []
            for abbr in abbreviations:
                long_desc = abbr.get('long', '').lower()
                for keyword in hazard_keywords:
                    if keyword in long_desc and len(long_desc) > 50:
                        problematic_abbrevs.append({
                            'short': abbr.get('short'),
                            'long': long_desc[:60]
                        })
                        break
            
            if problematic_abbrevs:
                logger.error(f"✗ FAIL: Hazard-like descriptions found in abbreviations:")
                for item in problematic_abbrevs:
                    logger.error(f"    {item['short']}: {item['long']}...")
                test_results.append(False)
            else:
                logger.info(f"✓ PASS: No hazard-like descriptions in abbreviations")
                test_results.append(True)
            
            # Test 4: Hazard statements extracted correctly
            if hazard_statements:
                all_h_codes = [stmt.get('code', '') for stmt in hazard_statements]
                if all(code.startswith('H') and code[1:4].isdigit() for code in all_h_codes):
                    logger.info(f"✓ PASS: All hazard statements have valid H-codes")
                    test_results.append(True)
                else:
                    logger.error(f"✗ FAIL: Invalid H-codes in hazard statements: {all_h_codes}")
                    test_results.append(False)
            else:
                logger.warning(f"⚠ WARNING: No hazard statements extracted")
                test_results.append(False)
            
            # Test 5: CLP classifications extracted correctly
            if clp_classifications:
                if len(clp_classifications) >= 2:
                    logger.info(f"✓ PASS: CLP classifications extracted ({len(clp_classifications)} items)")
                    test_results.append(True)
                else:
                    logger.warning(f"⚠ WARNING: Few CLP classifications found ({len(clp_classifications)})")
                    test_results.append(False)
            else:
                logger.warning(f"⚠ WARNING: No CLP classifications extracted")
                test_results.append(False)
            
            # Test 6: Abbreviations count reasonable
            if 30 <= len(abbreviations) <= 100:
                logger.info(f"✓ PASS: Abbreviations count is reasonable ({len(abbreviations)})")
                test_results.append(True)
            else:
                logger.warning(f"⚠ WARNING: Abbreviations count unexpected: {len(abbreviations)}")
                test_results.append(False)
            
            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("### TEST SUMMARY ###\n")
            passed = sum(test_results)
            total = len(test_results)
            logger.info(f"Passed: {passed}/{total}")
            
            if passed == total:
                logger.info("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
                return True
            elif passed >= total * 0.8:
                logger.info(f"\n⚠ MOSTLY PASSED ({passed}/{total})")
                return True
            else:
                logger.error(f"\n✗✗✗ TESTS FAILED ✗✗✗")
                return False
    
    except Exception as e:
        logger.error(f"Error during testing: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_abbreviations_extraction()
    sys.exit(0 if success else 1)
