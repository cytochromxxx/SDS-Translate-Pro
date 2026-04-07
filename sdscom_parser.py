#!/usr/bin/env python3
"""
SDScom XML Parser v6 (Final)
Extracts structured data from SDScom XML format into a detailed
key-value structure for the high-precision importer.
"""
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _get_text(element: ET.Element, path: str, default="") -> str:
    if element is None: return default
    node = element.find(path)
    return node.text.strip() if node is not None and node.text else default

def _get_recursive_text(element: ET.Element, default="") -> str:
    if element is None: return default
    return ' '.join(part.strip() for part in element.itertext() if part and part.strip())

class SDScomParser:
    def __init__(self):
        self.data = {}

    def parse(self, xml_path: str) -> Dict[str, Any]:
        logger.info(f"Parsing XML: {xml_path}")
        try:
            tree = ET.parse(xml_path)
            datasheet = tree.getroot().find('Datasheet')
            if datasheet is None: raise ValueError("<Datasheet> tag not found")

            self._parse_meta(datasheet)
            for i in range(1, 17):
                parse_func = getattr(self, f'_parse_section_{i}', None)
                if parse_func: parse_func(datasheet)
            
            return self.data
        except Exception as e:
            logger.error(f"Failed to parse XML: {e}", exc_info=True)
            return {}

    def _parse_meta(self, root):
        def format_date(d):
            if not d: return ""
            try:
                d = d.split('T')[0]
                parts = d.split('-')
                if len(parts) == 3:
                    return f"{parts[2]}.{parts[1]}.{parts[0]}"
            except Exception:
                pass
            return d

        self.data['meta'] = {
            'product_name': _get_text(root, './/ProductIdentity/TradeName'),
            'version': _get_text(root, './/IdentificationSubstPrep/VersionNo'),
            'revision_date': format_date(_get_text(root, './/IdentificationSubstPrep/IssueDate')),
            'print_date': format_date(_get_text(root, './/InformationFromExportingSystem/DateGeneratedExport'))
        }

    def _parse_section_1(self, root):
        section = root.find('IdentificationSubstPrep')
        if section is None: return
        self.data['s1_1_trade_name'] = _get_text(section, './/ProductIdentity/TradeName')
        self.data['s1_1_item_no'] = _get_text(section, 'ItemNo')
        self.data['s1_1_ufi'] = _get_text(section, './/ProductIdentity/Ufi')
        self.data['s1_2_use'] = _get_recursive_text(section.find('.//RelevantIdentifiedUse'))
        supplier = section.find('SupplierInformation')
        if supplier:
            self.data['s1_3_supplier_details'] = f"{_get_text(supplier, 'Name')}\n{_get_text(supplier, 'Address/PostAddressLine2')}\n{_get_text(supplier, 'Address/PostCode')} {_get_text(supplier, 'Address/PostCity')}"
            self.data['s1_3_phone'] = _get_text(supplier, 'Phone')
            self.data['s1_3_email'] = _get_text(supplier, 'Email')
            self.data['s1_3_website'] = _get_text(supplier, 'CompanyUrl')
        self.data['s1_4_emergency'] = _get_recursive_text(section.find('.//EmergencyPhone'))

    def _parse_section_2(self, root):
        section = root.find('HazardIdentification')
        if section is None: return
        self.data['s2_1_table'] = [{'class': _get_text(c, 'ClpHazardClassCategory'), 'statement': _get_recursive_text(c.find('ClpHazardStatement')), 'procedure': _get_recursive_text(c.find('ClpClassificationProcedure'))} for c in section.findall('.//ClpClassification/ClpHazardClassification')]
        labelling = section.find('.//HazardLabelling/ClpLabellingInfo')
        if labelling:
            self.data['s2_2_pictograms'] = [_get_text(p, 'PhraseCode') for p in labelling.findall('ClpHazardPictogram')]
            self.data['s2_2_signal_word'] = _get_recursive_text(labelling.find('ClpSignalWord'))
        self.data['s2_3_other_hazards'] = _get_recursive_text(section.find('OtherHazardsInfo'))

    def _parse_section_3(self, root):
        section = root.find('Composition')
        if section is None: return
        self.data['s3_2_table'] = []
        for c in section.findall('Component'):
            conc = c.find('Concentration')
            self.data['s3_2_table'].append({
                'identifiers': f"CAS No.: {_get_text(c, './/CasNo')}\nEC No.: {_get_text(c, './/EcNo')}",
                'name_class': f"<strong>{_get_text(c, './/GenericName')}</strong><br/>" + '<br/>'.join([_get_recursive_text(cl) for cl in c.findall('.//ClpHazardClassification')]),
                'concentration': f"{_get_text(conc, 'LowerValue')} - {_get_text(conc, 'UpperValue')}<br/>weight-%" if conc else ""
            })

    def _parse_section_4(self, root):
        section = root.find('FirstAidMeasures')
        if section is None: return
        desc = section.find('DescriptionOfFirstAidMeasures')
        if desc:
            self.data['s4_1_general'] = _get_recursive_text(desc.find('GeneralInformation'))
            self.data['s4_1_inhalation'] = _get_recursive_text(desc.find('FirstAidInhalation'))
            self.data['s4_1_skin'] = _get_recursive_text(desc.find('FirstAidSkin'))
            self.data['s4_1_eye'] = _get_recursive_text(desc.find('FirstAidEye'))
            self.data['s4_1_ingestion'] = _get_recursive_text(desc.find('FirstAidIngestion'))
        self.data['s4_2_symptoms'] = _get_recursive_text(section.find('InformationToHealthProfessionals'))
        self.data['s4_3_treatment'] = _get_recursive_text(section.find('MedicalAttentionAndSpecialTreatmentNeeded'))

    def _parse_section_5(self, root):
        section = root.find('FireFightingMeasures')
        if section is None: return
        self.data['s5_1_suitable'] = _get_recursive_text(section.find('.//MediaToBeUsed'))
        self.data['s5_1_unsuitable'] = _get_recursive_text(section.find('.//MediaNotBeUsed'))
        self.data['s5_2_hazards'] = _get_recursive_text(section.find('HazardCombustionProd'))
        self.data['s5_3_advice'] = _get_recursive_text(section.find('SpecialProtectiveEquipmentForFirefighters'))
        self.data['s5_4_additional'] = _get_recursive_text(section.find('FireAndExplosionComments'))

    def _parse_section_6(self, root):
        section = root.find('AccidentalReleaseMeasures')
        if section is None: return
        self.data['s6_1_non_emergency'] = _get_recursive_text(section.find('ForNonEmergencyPersonnel'))
        self.data['s6_1_emergency'] = _get_recursive_text(section.find('ForEmergencyResponders'))
        self.data['s6_2_env'] = _get_recursive_text(section.find('EnvironmentalPrecautions'))
        self.data['s6_3_containment'] = _get_recursive_text(section.find('.//Containment'))
        self.data['s6_3_cleanup'] = _get_recursive_text(section.find('.//CleaningUp'))
        self.data['s6_4_reference'] = _get_recursive_text(section.find('ReferenceToOtherSections'))

    def _parse_section_7(self, root):
        section = root.find('HandlingAndStorage')
        if section is None: return
        self.data['s7_1_handling'] = _get_recursive_text(section.find('SafeHandling'))
        self.data['s7_2_storage'] = _get_recursive_text(section.find('ConditionsForSafeStorage'))
        self.data['s7_3_end_use'] = _get_recursive_text(section.find('SpecificEndUses'))

    def _parse_section_8(self, root):
        section = root.find('ExposureControlPersonalProtection')
        if section is None: return
        # This section is complex with tables. For now, a simplified extraction.
        self.data['s8_1_params'] = _get_recursive_text(section.find('ControlParameters'))
        self.data['s8_2_controls'] = _get_recursive_text(section.find('PersonalProtectionEquipment'))

    def _parse_section_9(self, root):
        section = root.find('PhysicalChemicalProperties')
        if section is None: return
        self.data['s9_1_table'] = []
        rows = section.findall('.//SafetyRelevantInformation/*')
        for row in rows:
            name = row.tag
            value_node = row.find('.//Value') or row
            value = _get_recursive_text(value_node)
            self.data['s9_1_table'].append({'param': name, 'value': value})

    def _parse_section_10(self, root):
        section = root.find('StabilityReactivity')
        if section is None: return
        self.data['s10_1_reactivity'] = _get_recursive_text(section.find('ReactivityDescription'))
        self.data['s10_3_possibility'] = _get_recursive_text(section.find('HazardousReactions'))
        self.data['s10_4_conditions'] = _get_recursive_text(section.find('ConditionsToAvoid'))
        self.data['s10_5_materials'] = _get_recursive_text(section.find('MaterialsToAvoid'))
        self.data['s10_6_decomposition'] = _get_recursive_text(section.find('HazardousDecompositionProducts'))

    def _parse_section_11(self, root):
        section = root.find('ToxicologicalInformation')
        if section is None: return
        self.data['s11_info'] = _get_recursive_text(section)

    def _parse_section_12(self, root):
        section = root.find('EcologicalInformation')
        if section is None: return
        self.data['s12_info'] = _get_recursive_text(section)
        
    def _parse_section_13(self, root):
        section = root.find('DisposalConsiderations')
        if section is None: return
        self.data['s13_info'] = _get_recursive_text(section)

    def _parse_section_14(self, root):
        section = root.find('TransportInformation')
        if section is None: return
        self.data['s14_info'] = _get_recursive_text(section)

    def _parse_section_15(self, root):
        section = root.find('RegulatoryInfo')
        if section is None: return
        self.data['s15_info'] = _get_recursive_text(section)

    def _parse_section_16(self, root):
        section = root.find('OtherInformation')
        if section is None: return
        self.data['s16_info'] = _get_recursive_text(section)

def parse_sdscom_xml(xml_path: str) -> Dict[str, Any]:
    parser = SDScomParser()
    return parser.parse(xml_path)
