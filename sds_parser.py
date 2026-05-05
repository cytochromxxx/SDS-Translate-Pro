#!/usr/bin/env python3
"""
SDScom XML Parser v8
Extracts structured data from SDScom XML format using lxml for robust parsing.
"""

import logging
from lxml import etree
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_text(element: Optional[etree._Element], path: str, default: str = "") -> str:
    """Safely gets text content from an element using a truly namespace-agnostic XPath."""
    if element is None:
        return default
    try:
        # Correctly create a namespace-agnostic relative path
        agnostic_path = "./" + "/".join(
            [f"*[local-name()='{part}']" for part in path.split("/")]
        )
        nodes = element.xpath(agnostic_path)
        if nodes:
            return " ".join("".join(nodes[0].itertext()).strip().split())
        return default
    except Exception as e:
        logger.warning(f"XPath {path} failed with error: {e}")
        return default


def get_all_text_from_nodes(element: Optional[etree._Element], path: str) -> str:
    """Safely gets and joins text content from all found elements using a namespace-agnostic XPath."""
    if element is None:
        return ""
    try:
        agnostic_path = ".//" + "/".join(
            [f"*[local-name()='{part}']" for part in path.split("/")]
        )
        nodes = element.xpath(agnostic_path)
        if not nodes:
            return ""

        pieces = []
        for node in nodes:
            text = "".join(node.itertext()).strip()
            if text:
                pieces.append(text)

        res = " ".join(pieces)
        res = res.replace(" ,", ",")
        res = res.replace(",,", ",")
        return " ".join(res.split())
    except Exception as e:
        logger.warning(f"XPath {path} failed with error: {e}")
        return ""
    try:
        agnostic_path = ".//" + "/".join(
            [f"*[local-name()='{part}']" for part in path.split("/")]
        )
        nodes = element.xpath(agnostic_path)
        if not nodes:
            return ""
        text = " ".join("".join(node.itertext()).strip() for node in nodes).strip()
        return " ".join(text.split())
    except Exception as e:
        logger.warning(f"XPath {path} failed with error: {e}")
        return ""


def get_all_texts(element: Optional[etree._Element], path: str) -> List[str]:
    """Gets all text contents from a list of elements using a namespace-agnostic XPath."""
    if element is None:
        return []
    try:
        agnostic_path = ".//" + "/".join(
            [f"*[local-name()='{part}']" for part in path.split("/")]
        )
        return [node.text.strip() for node in element.xpath(agnostic_path) if node.text]
    except Exception:
        return []


class NewSDScomParser:
    def __init__(self, xml_path: str, pdf_path: Optional[str] = None):
        self.tree = etree.parse(xml_path)
        self.root = self.tree.getroot()
        self.pdf_path = pdf_path
        self.data: Dict[str, Any] = {}

    def _xpath_single(
        self, element: etree._Element, path: str
    ) -> Optional[etree._Element]:
        """Helper to get the first result of an xpath query."""
        if element is None:
            return None
        agnostic_path = "./" + "/".join(
            [f"*[local-name()='{part}']" for part in path.split("/")]
        )
        results = element.xpath(agnostic_path)
        return results[0] if results else None

    def parse(self) -> Dict[str, Any]:
        logger.info(f"Parsing XML with new parser: {self.tree.docinfo.URL}")
        datasheet_list = self.root.xpath("//*[local-name()='Datasheet']")
        if not datasheet_list:
            raise ValueError("<Datasheet> tag not found")
        self.datasheet = datasheet_list[
            0
        ]  # Store as instance variable for access in section parsers
        datasheet = self.datasheet

        self.data["meta"] = self._parse_meta(datasheet)

        sections = {
            1: "IdentificationSubstPrep",
            2: "HazardIdentification",
            3: "Composition",
            4: "FirstAidMeasures",
            5: "FireFightingMeasures",
            6: "AccidentalReleaseMeasures",
            7: "HandlingAndStorage",
            8: "ExposureControlPersonalProtection",
            9: "PhysicalChemicalProperties",
            10: "StabilityReactivity",
            11: "ToxicologicalInformation",
            12: "EcologicalInformation",
            13: "DisposalConsiderations",
            14: "TransportInformation",
            15: "RegulatoryInfo",
            16: "OtherInformation",
        }

        for num, section_name in sections.items():
            section_elements = datasheet.xpath(f"./*[local-name()='{section_name}']")
            if section_elements:
                parse_func = getattr(self, f"_parse_section_{num}", None)
                if parse_func:
                    parsed_data = parse_func(section_elements[0])
                    if num == 2 and "hazard_identification" in parsed_data:
                        self.data["hazard_identification"] = parsed_data[
                            "hazard_identification"
                        ]
                    if num == 16:
                        self.data["other_information"] = parsed_data.get(
                            "other_information", {}
                        )
                    else:
                        self.data[f"section_{num}"] = parsed_data

        # PDF gap filling: if a pdf_path was provided, fill empty XML fields from PDF
        if self.pdf_path:
            try:
                from pdf_gap_filler import SDSPDFGapFiller

                logger.info(f"Running PDF gap filler with: {self.pdf_path}")
                with SDSPDFGapFiller(self.pdf_path) as filler:
                    self.data = filler.fill_gaps(self.data)
                logger.info("PDF gap filling completed")
            except Exception as e:
                logger.warning(
                    f"PDF gap filling failed (continuing with XML-only data): {e}"
                )

        return self.data

    def _parse_meta(self, datasheet: etree._Element) -> Dict[str, str]:
        id_section = self._xpath_single(datasheet, "IdentificationSubstPrep")
        info_section = self._xpath_single(datasheet, "InformationFromExportingSystem")

        def format_date(d):
            if not d:
                return ""
            try:
                d = d.split("T")[0]
                parts = d.split("-")
                if len(parts) == 3:
                    return f"{parts[2]}.{parts[1]}.{parts[0]}"
            except Exception:
                pass
            return d

        return {
            "product_name": get_text(id_section, "ProductIdentity/TradeName"),
            "version": get_text(id_section, "VersionNo"),
            "revision_date": format_date(get_text(id_section, "RevisionDate")),
            "print_date": format_date(get_text(info_section, "DateGeneratedExport")),
            "language": get_text(info_section, "Language/FreetextLanguageCode"),
            "country": get_text(
                info_section,
                "RegulationsRelatedToCountryOrRegion/RegulationsRelatedToCountryOrRegionCode",
            ),
        }

    def _parse_section_1(self, section: etree._Element) -> Dict[str, Any]:
        supplier = self._xpath_single(section, "SupplierInformation")
        emergency = self._xpath_single(section, "EmergencyPhone")
        product_categories = section.xpath('.//*[local-name()="ProductCategory"]')
        pc1 = (
            ": ".join(
                filter(
                    None,
                    [
                        get_text(product_categories[0], "PcCode"),
                        get_text(product_categories[0], "PcFulltext/FullText"),
                    ],
                )
            )
            if len(product_categories) > 0
            else ""
        )
        pc2 = (
            ": ".join(
                filter(
                    None,
                    [
                        get_text(product_categories[1], "PcCode"),
                        get_text(product_categories[1], "PcFulltext/FullText"),
                    ],
                )
            )
            if len(product_categories) > 1
            else ""
        )
        lcs_elem = section.xpath('.//*[local-name()="LifeCycleStage"]')
        lcs = (
            ": ".join(
                filter(
                    None,
                    [
                        get_text(lcs_elem[0], "LcsCode"),
                        get_text(lcs_elem[0], "LcsFulltext/FullText"),
                    ],
                )
            )
            if lcs_elem
            else ""
        )

        product_type = get_all_text_from_nodes(section, "RelevantIdentifiedUse/ProductType/FullText")
        su = get_text(section, "RelevantIdentifiedUse/IdentifiedUse/SectorOfUse/SuCode")
        su_fulltext = get_text(section, "RelevantIdentifiedUse/IdentifiedUse/SectorOfUse/SuFulltext/FullText")
        
        # Fallback to "No data available" if no relevant uses data is present
        if not product_type and not su and not pc1 and not pc2 and not lcs:
            product_type = "No data available"

        return {
            "product_identifier": {
                "trade_name": get_text(section, "ProductIdentity/TradeName"),
                "item_no": get_text(section, "ItemNo"),
                "ufi": get_text(section, "ProductIdentity/Ufi"),
            },
            "relevant_uses": {
                "product_type": product_type,
                "su": su,
                "su_fulltext": su_fulltext,
                "pc1": pc1,
                "pc2": pc2,
                "lcs": lcs,
            },
            "supplier_details": {
                "name": get_text(supplier, "Name"),
                "address": f"{get_text(supplier, 'Address/PostAddressLine2')}, {get_text(supplier, 'Address/PostCode')} {get_text(supplier, 'Address/PostCity')}",
                "country": get_text(supplier, "Country"),
                "phone": get_text(supplier, "Phone"),
                "email": get_text(supplier, "Email"),
                "website": get_text(supplier, "CompanyUrl"),
            },
            "emergency_phone": {
                "number": get_text(emergency, "No"),
                "description": get_text(
                    emergency, "EmergencyPhoneDescription/FullText"
                ),
            },
        }

    def _parse_section_2(self, section: etree._Element) -> Dict[str, Any]:
        hazard_labelling = self._xpath_single(section, "HazardLabelling")
        labelling = self._xpath_single(hazard_labelling, "ClpLabellingInfo")
        clp_classifications = [
            {
                "clp_hazard_class_category": get_text(c, "ClpHazardClassCategory"),
                "clp_hazard_statement_code": get_text(
                    c, "ClpHazardStatement/PhraseCode"
                ),
                "clp_hazard_statement_text": get_all_text_from_nodes(
                    c, "ClpHazardStatement/FullText"
                ),
                "clp_classification_procedure": get_all_text_from_nodes(
                    c, "ClpClassificationProcedure/FullText"
                ),
            }
            for c in section.xpath('.//*[local-name()="ClpHazardClassification"]')
        ]

        # New logic for precautionary statements
        prevention_stmts = []
        response_stmts = []

        if labelling is not None:
            all_statements = labelling.xpath(
                ".//*[local-name()='ClpPrecautionaryStatement']"
            )

            for stmt in all_statements:
                # Get ALL PhraseCode elements (not just the first one)
                codes = get_all_texts(stmt, "PhraseCode")
                text = get_all_text_from_nodes(stmt, "FullText")

                if codes and text:
                    # Clean each code: remove sub-codes like .4 and prefix with 'P'
                    clean_codes = []
                    for code in codes:
                        clean_code = code.split(".")[0]
                        clean_codes.append(f"P{clean_code}")

                    full_code = " + ".join(clean_codes)

                    # Determine category based on the first code
                    if clean_codes and clean_codes[0].startswith("P2"):
                        prevention_stmts.append({"code": full_code, "text": text})
                    elif clean_codes and clean_codes[0].startswith("P3"):
                        response_stmts.append({"code": full_code, "text": text})

        # Extract hazard components from the composition section
        hazard_components = []
        composition = self._xpath_single(self.datasheet, "Composition")
        if composition is not None:
            for comp in composition.xpath('.//*[local-name()="Component"]'):
                comp_name = get_text(comp, "Substance/GenericName")
                if comp_name:
                    hazard_components.append(comp_name)

        return {
            "hazard_identification": {"clp_classifications": clp_classifications},
            "classification": [
                {
                    "category": get_text(c, "ClpHazardClassCategory"),
                    "statement": get_all_text_from_nodes(
                        c, "ClpHazardStatement/FullText"
                    ),
                    "code": get_text(c, "ClpHazardStatement/PhraseCode"),
                    "procedure": get_all_text_from_nodes(
                        c, "ClpClassificationProcedure/FullText"
                    ),
                }
                for c in section.xpath('.//*[local-name()="ClpHazardClassification"]')
            ],
            "labelling": {
                "pictograms": get_all_texts(labelling, "ClpHazardPictogram/PhraseCode"),
                "signal_word": get_text(labelling, "ClpSignalWord/FullText"),
                "hazard_components": ", ".join(hazard_components)
                if hazard_components
                else None,
                "hazard_statements": [
                    {
                        "code": get_text(s, "PhraseCode"),
                        "text": get_all_text_from_nodes(s, "FullText"),
                    }
                    for s in labelling.xpath('.//*[local-name()="ClpHazardStatement"]')
                ]
                if labelling is not None
                else [],
                "precautionary_statements": {
                    "prevention": prevention_stmts,
                    "response": response_stmts,
                },
            },
            "other_hazards": {
                "physicochemical": get_all_text_from_nodes(
                    section, "OtherHazardsInfo/PhysicochemicalEffect/FullText"
                ),
                "health": get_all_text_from_nodes(
                    section, "OtherHazardsInfo/HealthEffect/FullText"
                ),
            },
        }

    def _parse_section_3(self, section: etree._Element) -> Dict[str, Any]:
        components = []
        for c in section.xpath('.//*[local-name()="Component"]'):
            lower_conc = get_text(c, "Concentration/LowerValue")
            upper_conc = get_text(c, "Concentration/UpperValue")
            unit_conc = get_text(c, "Concentration/Unit")
            if lower_conc and upper_conc:
                conc_str = f"{lower_conc} - < {upper_conc} {unit_conc}"
            else:
                conc_str = f"{lower_conc or upper_conc} {unit_conc}"

            component_data = {
                "name": get_text(c, "Substance/GenericName"),
                "cas": get_text(c, "Substance/CasNo"),
                "ec": get_text(c, "Substance/EcNo"),
                "reach_no": get_text(
                    c, "Substance/ReachRegistration/RegistrationNumber"
                ),
                "index_no": get_text(c, "Substance/IndexNo"),
                "concentration": conc_str,
                "classification": [
                    f"{get_text(cl, 'ClpHazardClassCategory')} (H{get_text(cl, 'ClpHazardStatement/PhraseCode')}): {get_all_text_from_nodes(cl, 'ClpHazardStatement/FullText')}"
                    for cl in c.xpath('.//*[local-name()="ClpHazardClassification"]')
                ],
                "toxicological_info": [],
                "ate_values": [],
                "pictograms": get_all_texts(c, "ClpHazardPictogram/PhraseCode"),
                "signal_word": get_text(c, "ClpSignalWord/FullText"),
            }
            tox_info = self._xpath_single(c, "ToxicologicalInformation")
            if tox_info is not None:
                for test_result in tox_info.xpath('.//*[local-name()="TestResults"]'):
                    effect = get_text(test_result, "EffectTested")
                    route = get_text(test_result, "ExposureRoute")
                    val_node = test_result.xpath('.//*[local-name()="Value"]')
                    exact = get_text(val_node[0], "ExactValue") if val_node else ""
                    lower = get_text(val_node[0], "LowerValue") if val_node else ""
                    upper = get_text(val_node[0], "UpperValue") if val_node else ""
                    sym = (
                        get_text(val_node[0], "LowerValueSymbol")
                        or get_text(val_node[0], "UpperValueSymbol")
                        if val_node
                        else ""
                    )
                    unit = get_text(val_node[0], "Unit") if val_node else "mg/kg"
                    raw_num = exact or lower or upper
                    try:
                        num = float(raw_num)
                        formatted = f"{num:,g}"
                        if sym in (">", "gt", "GT"):
                            formatted = f"&gt; {formatted}"
                    except ValueError:
                        formatted = raw_num
                    route_lower = route.lower()
                    if "oral" in route_lower:
                        label = "ATE (oral)"
                    elif "dermal" in route_lower:
                        label = "ATE (dermal)"
                    elif "vapour" in route_lower or "vapor" in route_lower:
                        label = "ATE (inhalation, vapour)"
                    elif "dust" in route_lower or "mist" in route_lower:
                        label = "ATE (inhalation, dust/mist)"
                    elif "inhal" in route_lower:
                        label = "ATE (inhalation)"
                    else:
                        label = f"ATE ({route.lower()})" if route else effect
                    component_data["ate_values"].append(
                        {"label": label, "value": formatted, "unit": unit}
                    )

                    # Create toxicological_info matching test.html formatting
                    species = get_text(test_result, "Species")
                    species_str = f" ({species})" if species else ""
                    dose = get_text(test_result, "EffectDose")
                    method = get_text(test_result, "Method")
                    method_str = f" {method}" if method else ""

                    exp_time = get_text(test_result, "ExposureTime")
                    exp_time_str = f" {exp_time}" if exp_time else ""

                    dose_label = (
                        dose
                        if dose
                        else ("LC50" if route.lower() == "inhalation" else "LD50")
                    )
                    tox_str = f"{dose_label} {route.lower()}: {formatted} {unit}{exp_time_str}{species_str}{method_str}"
                    if route.lower() == "inhalation":
                        effect_tested = effect.lower() if effect else ""
                        if "vapour" in effect_tested or "vapor" in effect_tested:
                            tox_str = f"LC50 Acute inhalation toxicity (vapour): {formatted} {unit}{exp_time_str}{species_str}{method_str}"
                        elif "dust" in effect_tested or "mist" in effect_tested:
                            tox_str = f"LC50 Acute inhalation toxicity (dust/mist): {formatted} {unit}{exp_time_str}{species_str}{method_str}"

                    component_data["toxicological_info"].append(tox_str)
            components.append(component_data)
        return {"mixture_components": components}

    def _parse_section_4(self, section: etree._Element) -> Dict[str, Any]:
        desc = self._xpath_single(section, "DescriptionOfFirstAidMeasures")
        return {
            "description": {
                "general": get_all_text_from_nodes(desc, "GeneralInformation/FullText"),
                "inhalation": get_all_text_from_nodes(
                    desc, "FirstAidInhalation/FullText"
                ),
                "skin": get_all_text_from_nodes(desc, "FirstAidSkin/FullText"),
                "eye": get_all_text_from_nodes(desc, "FirstAidEye/FullText"),
                "ingestion": get_all_text_from_nodes(
                    desc, "FirstAidIngestion/FullText"
                ),
                "self_protection": get_text(
                    desc, "PersonalProtectionFirstAider/FullText"
                ),
            },
            "symptoms": get_all_text_from_nodes(
                section,
                "InformationToHealthProfessionals/SymptomsAndEffectsGeneral/FullText",
            ),
            "treatment": get_all_text_from_nodes(
                section,
                "MedicalAttentionAndSpecialTreatmentNeeded/MedicalTreatment/FullText",
            ),
        }

    def _parse_section_5(self, section: etree._Element) -> Dict:
        return {
            "suitable_media": get_all_text_from_nodes(
                section, "ExtinguishingMedia/MediaToBeUsed"
            ) or "No data available",
            "unsuitable_media": get_text(section, "ExtinguishingMedia/MediaNotBeUsed") or "No data available",
            "special_hazards": get_all_text_from_nodes(
                section, "FireAndExplosionHazards"
            ) or "No data available",
            "combustion_products": get_all_text_from_nodes(
                section, "HazardCombustionProd"
            ) or "No data available",
            "firefighter_advice": get_all_text_from_nodes(
                section, "SpecialProtectiveEquipmentForFirefighters"
            ) or "No data available",
            "additional_info": get_all_text_from_nodes(
                section, "FireAndExplosionComments"
            ) or "No data available",
        }

    def _parse_section_6(self, section: etree._Element) -> Dict:
        return {
            "personal_precautions": get_all_text_from_nodes(
                section, "ForNonEmergencyPersonnel/PersonalPrecautions"
            ) or "No data available",
            "protective_equipment": get_text(
                section, "ForNonEmergencyPersonnel/ProtectiveEquipment"
            ) or "No data available",
            "emergency_responders": get_text(section, "ForEmergencyResponders") or "No data available",
            "environmental_precautions": get_text(section, "EnvironmentalPrecautions") or "No data available",
            "containment": get_text(section, "ContainmentAndCleaningUp/Containment") or "No data available",
            "cleaning": get_text(section, "ContainmentAndCleaningUp/CleaningUp") or "No data available",
            "other_sections": get_all_text_from_nodes(
                section, "ReferenceToOtherSections"
            ) or "No data available",
            "additional_info": get_text(section, "AdditionalInformation") or "No data available",
        }

    def _parse_section_7(self, section: etree._Element) -> Dict:
        return {
            "safe_handling": get_all_text_from_nodes(
                section, "SafeHandling/HandlingPrecautions"
            ) or "No data available",
            "fire_prevention": get_all_text_from_nodes(
                section, "SafeHandling/PrecautionaryMeasures/MeasuresToPreventFire"
            ) or "No data available",
            "occupational_hygiene": get_all_text_from_nodes(
                section, "SafeHandling/GeneralOccupationalHygiene"
            ) or "No data available",
            "storage_conditions": get_all_text_from_nodes(
                section,
                "ConditionsForSafeStorage/TechnicalMeasuresAndStorageConditions",
            ) or "No data available",
            "storage_rooms": get_all_text_from_nodes(
                section,
                "ConditionsForSafeStorage/RequirementsForStorageRoomsAndVessels",
            ) or "No data available",
            "storage_assembly": get_all_text_from_nodes(
                section, "ConditionsForSafeStorage/HintsOnStorageAssembly"
            ) or "No data available",
            "further_storage_conditions": get_all_text_from_nodes(
                section,
                "ConditionsForSafeStorage/FurtherInformationOnStorageConditions",
            ) or "No data available",
            "specific_end_use": get_text(section, "SpecificEndUses") or "No data available",
        }

    def _parse_section_8(self, section: etree._Element) -> Dict:
        # Extract Occupational Exposure Limits (OEL) from XML
        oel_limits = []

        # Try to find OEL data in the XML
        oel_elements = section.xpath('.//*[local-name()="OccupationalExposureLimit"]')
        for oel in oel_elements:
            oel_entry = {
                "substance": get_text(oel, "SubstanceName"),
                "CAS_number": get_text(oel, "CasNo"),
                "limit_value": get_text(oel, "ExposureLimitValue"),
                "limit_unit": get_text(oel, "Unit"),
                "limit_type": get_text(oel, "LimitType"),
                "time_weight_average": get_text(oel, "TimeWeightedAverage"),
                "short_term_limit": get_text(oel, "ShortTermExposureLimit"),
                "regulatory_reference": get_all_text_from_nodes(
                    oel, "RegulatorySource/FullText"
                ),
            }
            if oel_entry.get("substance") or oel_entry.get("limit_value"):
                oel_limits.append(oel_entry)

        # Also check for DNEL (Derived No Effect Level) values
        dnel_values = []
        dnel_elements = section.xpath('.//*[local-name()="DNEL"]')
        for dnel in dnel_elements:
            dnel_entry = {
                "exposure_route": get_text(dnel, "ExposureRoute"),
                "exposure_frequency": get_text(dnel, "ExposureFrequency"),
                "value": get_text(dnel, "Value"),
                "unit": get_text(dnel, "Unit"),
                "population": get_text(dnel, "Population"),
            }
            if dnel_entry.get("value"):
                dnel_values.append(dnel_entry)

        control_params = get_all_text_from_nodes(section, "ControlParameters")
        if not oel_limits and not dnel_values and not control_params:
            control_params = "No data available"
            
        env_exposure = get_text(section, "EnvironmentalExposureControls")
        if not env_exposure:
            env_exposure = "No data available"

        eng_controls = get_all_text_from_nodes(section, "AppropriateEngineeringControls")
        if not eng_controls:
            # Fallback for XMLs (e.g., GeSi³) that put engineering controls into ControlParametersComments
            eng_controls = get_all_text_from_nodes(section, "ControlParametersComments")
        if not eng_controls:
            eng_controls = "No data available"

        # Parse Biological Limit Values into a list of dicts
        biological_limits = []
        blv_elements = section.xpath('.//*[local-name()="BiologicalLimitValue"]')
        for blv in blv_elements:
            blv_entry = {
                "limit_type": get_text(blv, "LimitType"),
                "substance": get_text(blv, "SubstanceName"),
                "CAS_number": get_text(blv, "CasNo"),
                "EC_number": get_text(blv, "EcNo"),
                "limit_value": get_text(blv, "ExposureLimitValue"),
                "parameter": get_all_text_from_nodes(blv, "Parameter"),
                "test_material": get_all_text_from_nodes(blv, "TestMaterial"),
                "sampling_time": get_all_text_from_nodes(blv, "SamplingTime"),
                "remark": get_all_text_from_nodes(blv, "Remarks"),
            }
            # Only include if there's at least one core field (substance, limit_value, CAS_number, EC_number, limit_type)
            core_fields = [
                blv_entry.get("substance"),
                blv_entry.get("limit_value"),
                blv_entry.get("CAS_number"),
                blv_entry.get("EC_number"),
                blv_entry.get("limit_type"),
            ]
            if any(core_fields):
                biological_limits.append(blv_entry)

        return {
            "occupational_exposure_limits": oel_limits,
            "dnel_values": dnel_values,
            "control_parameters_comments": control_params,
            "engineering_controls": eng_controls,
            "biological_limit_values": biological_limits,
            "respiratory_protection": get_all_text_from_nodes(
                section, "PersonalProtectionEquipment/RespiratoryProtection"
            ) or "No data available",
            "eye_protection": get_all_text_from_nodes(
                section, "PersonalProtectionEquipment/EyeProtection"
            ) or "No data available",
            "skin_protection": get_all_text_from_nodes(
                section, "PersonalProtectionEquipment/SkinProtection"
            ) or "No data available",
            "other_protection": get_all_text_from_nodes(
                section, "PersonalProtectionEquipment/OtherProtectionMeasures"
            ) or "No data available",
            "body_protection": get_all_text_from_nodes(
                section, "PersonalProtectionEquipment/OtherProtectionMeasures"
            ) or "No data available",
            "environmental_exposure": env_exposure,
        }

    def _parse_section_9(self, section: etree._Element) -> Dict:
        def _get_prop(element: Optional[etree._Element]):
            if element is None:
                return "No data available", "", ""

            def format_value(val_node):
                if val_node is None:
                    return ""
                symbol = get_text(val_node, "LowerValueSymbol") or get_text(
                    val_node, "UpperValueSymbol"
                )
                sym_map = {
                    "gt": ">",
                    "lt": "<",
                    "ge": ">=",
                    "le": "<=",
                    "eq": "=",
                    "ca": "ca.",
                }
                symbol = sym_map.get(symbol.lower(), symbol)
                value = (
                    get_text(val_node, "LowerValue")
                    or get_text(val_node, "UpperValue")
                    or get_text(val_node, "ExactValue")
                )
                unit = get_text(val_node, "Unit")
                parts = [p for p in [symbol, value, unit] if p]
                return " ".join(parts) if parts else ""

            value_nodes = element.xpath(
                ".//*[local-name()='UnitValue' or local-name()='Value']"
            )
            if len(value_nodes) > 1:
                value_str = " - ".join(
                    filter(None, [format_value(v) for v in value_nodes[:2]])
                )
            elif len(value_nodes) == 1:
                value_str = format_value(value_nodes[0])
            else:
                value_str = get_all_text_from_nodes(element, ".")
            if not value_str:
                other_desc = get_text(element, "OtherMediumDescription/FullText")
                if other_desc:
                    value_str = other_desc

            # Robustly find Temperature and Method anywhere below the current element
            temp_val_node = element.xpath(
                ".//*[local-name()='Temperature']/*[local-name()='ExactValue']"
            )
            temp = (
                temp_val_node[0].text.strip()
                if temp_val_node and temp_val_node[0].text
                else ""
            )
            if temp:
                temp_unit_node = element.xpath(
                    ".//*[local-name()='Temperature']/*[local-name()='Unit']"
                )
                unit = (
                    temp_unit_node[0].text.strip()
                    if temp_unit_node and temp_unit_node[0].text
                    else ""
                )
                temp = f"{temp} {unit}"

            method_node = element.xpath(
                ".//*[local-name()='Method']/*[local-name()='FullText']"
            )
            method = (
                method_node[0].text.strip()
                if method_node and method_node[0].text
                else ""
            )

            return value_str or "No data available", temp, method

        safety_info_node = self._xpath_single(section, "SafetyRelevantInformation")
        safety_data = []
        if safety_info_node is not None:
            parameters = [
                ("pH", "PhValue"),
                ("Melting point", "MeltingPointRelated"),
                ("Freezing point", "FreezingPoint"),
                ("Initial boiling point and boiling range", "BoilingPointRelated"),
                ("Flash point", "FlashPoint"),
                ("Evaporation rate", "EvaporationRate"),
                ("Auto-ignition temperature", "AutoIgnitionTemperature"),
                ("Upper/lower flammability or explosive limits", "ExplosionLimit"),
                ("Vapour pressure", "VapourPressure"),
                ("Vapour density", "VapourDensity"),
                ("Density", "Densities"),
                ("Bulk density", "BulkDensity"),
                ("Water solubility", "Solubilities"),
                ("Dynamic viscosity", "DynamicViscosity"),
                ("Kinematic viscosity", "KinematicViscosity"),
            ]
            for name, tag in parameters:
                child_node = next(
                    (child for child in safety_info_node if child.tag.endswith(tag)),
                    None,
                )
                val, temp, meth = _get_prop(child_node)
                safety_data.append(
                    {
                        "parameter": name,
                        "value": val,
                        "temperature": temp,
                        "method": meth,
                    }
                )

        appearance_node = self._xpath_single(section, "Appearance")
        appearance_parts = []
        if appearance_node is not None:
            form = get_text(appearance_node, "Form")
            if form and form.lower() != "other":
                appearance_parts.append(f"Form: {form}")
            state = get_text(appearance_node, "PhysicalState/FullText") or get_text(
                appearance_node, "PhysicalState"
            )
            if state:
                appearance_parts.append(f"Physical state: {state}")
            color = get_text(appearance_node, "ColourDescription/FullText")
            if color:
                appearance_parts.append(f"Color: {color}")
            odour = get_text(appearance_node, "Odour/FullText")
            if odour:
                appearance_parts.append(f"Odour: {odour}")
        appearance_str = "<br>".join(appearance_parts)

        return {"appearance": appearance_str, "safety_data": safety_data}

    def _parse_section_10(self, section: etree._Element) -> Dict:
        return {
            "reactivity": get_text(section, "ReactivityDescription") or "No data available",
            "chemical_stability": get_text(section, "StabilityDescription") or "No data available",
            "hazardous_reactions": get_all_text_from_nodes(
                section, "HazardousReactions"
            ) or "No data available",
            "conditions_to_avoid": get_all_text_from_nodes(
                section, "ConditionsToAvoid"
            ) or "No data available",
            "incompatible_materials": get_all_text_from_nodes(
                section, "MaterialsToAvoid"
            ) or "No data available",
            "hazardous_decomposition": get_all_text_from_nodes(
                section, "HazardousDecompositionProducts"
            ) or "No data available",
        }

    def _parse_section_11(self, section: etree._Element) -> Dict:
        return {
            "acute_toxicity": get_all_text_from_nodes(section, "AcuteToxicity") or "No data available",
            "skin_corrosion": get_all_text_from_nodes(
                section, "SkinCorrosionIrritation"
            ) or "No data available",
            "eye_damage": get_all_text_from_nodes(section, "EyeDamageOrIrritation") or "No data available",
            "sensitisation": get_all_text_from_nodes(
                section, "RespiratoryOrSkinSensitisation"
            ) or "No data available",
            "mutagenicity": get_all_text_from_nodes(section, "GermCellMutagenicity") or "No data available",
            "carcinogenicity": get_all_text_from_nodes(section, "Carcinogenicity") or "No data available",
            "reproductive_toxicity": get_all_text_from_nodes(
                section, "ReproductiveToxicity"
            ) or "No data available",
            "stot_single": get_all_text_from_nodes(section, "SpecificTargetOrganSE") or "No data available",
            "stot_repeated": get_all_text_from_nodes(section, "SpecificTargetOrganRE") or "No data available",
            "aspiration_hazard": get_all_text_from_nodes(section, "AspirationHazard") or "No data available",
        }

    def _parse_section_12(self, section: etree._Element) -> Dict:
        def _format_value(val_node):
            if val_node is None:
                return ""
            symbol = get_text(val_node, "LowerValueSymbol") or get_text(
                val_node, "UpperValueSymbol"
            )
            sym_map = {
                "gt": ">",
                "lt": "<",
                "ge": ">=",
                "le": "<=",
                "eq": "=",
                "ca": "ca.",
            }
            symbol = sym_map.get(symbol.lower(), symbol)
            value = (
                get_text(val_node, "LowerValue")
                or get_text(val_node, "UpperValue")
                or get_text(val_node, "ExactValue")
            )
            try:
                if value:
                    v_float = float(value)
                    if v_float.is_integer():
                        value = f"{int(v_float):,}"
                    else:
                        value = f"{v_float:,g}"
            except ValueError:
                pass
            unit = get_text(val_node, "Unit")
            parts = [p for p in [symbol, value, unit] if p]
            return " ".join(parts)

        ecotox_components = []
        datasheet = section.getparent()
        if datasheet is None:
            return {"ecotox_components": []}
        composition = self._xpath_single(datasheet, "Composition")
        if composition is None:
            return {"ecotox_components": []}
        for c in composition.xpath('.//*[local-name()="Component"]'):
            component_data = {
                "generic_name": get_text(c, "Substance/GenericName"),
                "cas_no": get_text(c, "Substance/CasNo"),
                "ec_no": get_text(c, "Substance/EcNo"),
                "aquatic_toxicity_entries": [],
                "biodegradation": "",
                "bcf": "",
                "log_kow": "",
                "pbt_result": get_all_text_from_nodes(
                    c, "ResultsPbtAndVpvbAssessment/FullText"
                ),
            }
            eco_info = self._xpath_single(c, "EcologicalInformation")
            if eco_info is not None:
                for aquatic_test in eco_info.xpath(".//AquaticToxicity/*"):
                    value_node = self._xpath_single(aquatic_test, "Value")
                    entry = {
                        "effect_dose": get_text(
                            aquatic_test, "EffectDoseConcentration"
                        ),
                        "value": _format_value(value_node),
                        "exposure_time": get_all_text_from_nodes(
                            aquatic_test, "ExposureTime"
                        ),
                        "species": get_all_text_from_nodes(aquatic_test, "Species"),
                        "method": get_all_text_from_nodes(
                            aquatic_test, "Method/FullText"
                        ),
                    }
                    if entry["value"] or entry["effect_dose"]:
                        component_data["aquatic_toxicity_entries"].append(entry)
                bio_node = self._xpath_single(eco_info, "Bioaccumulation")
                if bio_node is not None:
                    component_data["bcf"] = _format_value(
                        self._xpath_single(bio_node, "BioconcentrationFactor/Value")
                    )
                    component_data["log_kow"] = _format_value(
                        self._xpath_single(bio_node, "LogKow/Value")
                    )
                persist_node = self._xpath_single(eco_info, "PersistenceDegradability")
                if persist_node is not None:
                    component_data["biodegradation"] = get_all_text_from_nodes(
                        persist_node, "Biodegradation/FullText"
                    )
            ecotox_components.append(component_data)
        return {
            "ecotox_components": ecotox_components,
            "mobility_info": get_all_text_from_nodes(section, "Mobility") or "No data available",
            "endocrine_disrupting_info": get_all_text_from_nodes(
                section, "EndocrineDisruptingProperties"
            ) or "No data available",
            "other_adverse_effects_info": get_all_text_from_nodes(
                section, "OtherAdverseEffects"
            ) or "No data available",
            "persistence": get_all_text_from_nodes(section, "PersistenceDegradability") or "No data available",
            "bioaccumulation": get_all_text_from_nodes(section, "Bioaccumulation") or "No data available",
            "pbt_result": get_all_text_from_nodes(section, "ResultsPbtAndVpvbAssessment") or "No data available",
        }

    def _parse_section_13(self, section: etree._Element) -> Dict:
        waste_treatment_nodes = section.xpath(
            './/*[local-name()="WasteTreatment"]//*[local-name()="FullText"]/text()'
        )
        waste_treatment = " ".join(
            filter(None, [t.strip() for t in waste_treatment_nodes])
        )
        if not waste_treatment:
            waste_treatment = "No data available"

        eu_requirements = get_all_text_from_nodes(
            section, "EuRequirements/EuWasteRegulations/FullText"
        )

        ewl_product = self._xpath_single(
            section, "EuRequirements/EuropeanWasteList/EWLProduct"
        )
        ewl_packing = self._xpath_single(
            section, "EuRequirements/EuropeanWasteList/EWLPacking"
        )

        ewl_data = []
        if ewl_product is not None:
            ewl_data.append(
                {
                    "type": "Product",
                    "code": get_text(ewl_product, "WasteCode"),
                    "description": get_text(ewl_product, "WasteDescription/FullText"),
                    "hazardous": get_text(ewl_product, "HazardousWaste"),
                }
            )
        if ewl_packing is not None:
            ewl_data.append(
                {
                    "type": "Packaging",
                    "code": get_text(ewl_packing, "WasteCode"),
                    "description": get_text(ewl_packing, "WasteDescription/FullText"),
                    "hazardous": get_text(ewl_packing, "HazardousWaste"),
                }
            )

        if not ewl_data:
            ewl_data = [
                {
                    "type": "Product",
                    "code": "No data available",
                    "description": "",
                    "hazardous": ""
                }
            ]

        regulation_text = get_text(
            section, "EuRequirements/EuWasteRegulations/FullText"
        )

        return {
            "waste_treatment": waste_treatment,
            "eu_requirements": eu_requirements,
            "ewl_data": ewl_data,
            "waste_code_product": ewl_data[0]["code"] if ewl_data else "No data available",
            "waste_code_product_desc": ewl_data[0]["description"] if ewl_data else "",
            "regulation_text": regulation_text,
        }

    def _parse_section_14(self, section: etree._Element) -> Dict:
        def _get_shipping_name(
            transport_node: Optional[etree._Element],
            name_path: str,
            substance_paths: List[str],
        ):
            if transport_node is None:
                return ""
            name = get_text(transport_node, name_path) or ""
            substances = []
            for path in substance_paths:
                found_substances = get_all_texts(transport_node, path)
                if found_substances:
                    substances.extend(found_substances)
            if substances:
                unique_substances = list(dict.fromkeys(substances))
                name += f" ({', '.join(unique_substances)})"
            return name

        adr_rid_node = self._xpath_single(
            section, "TransportHazardClassification/AdrRid"
        )
        adr_rid_other_node = self._xpath_single(
            section, "OtherTransportInformation/AdrRidOtherInformation"
        )
        # TODO: hardcoded - fallback values ('3', '274 | 601', '5 L', 'E1', '30', 'D/E') should come from XML/PDF extraction
        land_data = {
            "un_number": (
                "UN " + get_text(section, "UnNo/UnNoAdrRid")
                if get_text(section, "UnNo/UnNoAdrRid")
                else ""
            ),
            "shipping_name": _get_shipping_name(
                self._xpath_single(section, "ProperShippingName/AdrRid"),
                "ProperShippingNameNationalAdrRid/FullText",
                ["DangerReleasingSubstanceNationalAdrRid/FullText"],
            ),
            "transport_class": get_text(adr_rid_node, "ClassAdrRid"),
            "packing_group": get_text(section, "PackingGroup/PackingGroupAdrRid"),
            "environmental_hazards": get_text(
                section, "EnvironmentalHazards/EnvironmHazardAccordAdrRid/FullText"
            ),
            "special_provisions": get_text(
                adr_rid_other_node, "AdrRidSpecialProvisions"
            ),
            "limited_quantity": get_text(adr_rid_other_node, "AdrRidLimitedQty"),
            "excepted_quantities": get_text(adr_rid_other_node, "AdrRidExceptedQty"),
            "hazard_id": get_text(adr_rid_other_node, "AdrHazardIdentificationNo"),
            "classification_code": get_text(adr_rid_node, "ClassCodeAdrRid"),
            "tunnel_code": get_text(adr_rid_other_node, "AdrTunnelRestrictionCode"),
        }
        adn_node = self._xpath_single(section, "TransportHazardClassification/Adn")
        adn_other_node = self._xpath_single(
            section, "OtherTransportInformation/AdnOtherInformation"
        )
        # TODO: hardcoded - fallback values ('3', '274 | 601', '5 L', 'E1') should come from XML/PDF extraction
        inland_data = {
            "un_number": (
                "UN " + get_text(section, "UnNo/UnNoAdn")
                if get_text(section, "UnNo/UnNoAdn")
                else ""
            ),
            "shipping_name": _get_shipping_name(
                self._xpath_single(section, "ProperShippingName/Adn"),
                "ProperShippingNameNationalAdn/FullText",
                ["DangerReleasingSubstanceNationalAdn/FullText"],
            ),
            "transport_class": get_text(adn_node, "ClassAdn"),
            "packing_group": get_text(section, "PackingGroup/PackingGroupAdn"),
            "environmental_hazards": get_text(
                section, "EnvironmentalHazards/EnvironmHazardAccordAdn/FullText"
            ),
            "special_provisions": get_text(adn_other_node, "AdnSpecialProvisions"),
            "limited_quantity": get_text(adn_other_node, "AdnLimitedQty"),
            "excepted_quantities": get_text(adn_other_node, "AdnExceptedQty"),
            "classification_code": get_text(adn_node, "ClassCodeAdn"),
        }
        imdg_node = self._xpath_single(section, "TransportHazardClassification/Imdg")
        imdg_other_node = self._xpath_single(
            section, "OtherTransportInformation/ImdgOtherInformation"
        )
        # TODO: hardcoded - fallback values ('3', '223 | 274', '5 L', 'E1', 'F-E, S-D') should come from XML/PDF extraction
        sea_data = {
            "un_number": (
                "UN " + get_text(section, "UnNo/UnNoImdg")
                if get_text(section, "UnNo/UnNoImdg")
                else ""
            ),
            "shipping_name": _get_shipping_name(
                self._xpath_single(section, "ProperShippingName/Imdg"),
                "ProperShippingNameEnglishImdg/FullText",
                ["DangerReleasingSubstanceEnglishImdg/FullText"],
            ),
            "transport_class": get_text(imdg_node, "ClassImdg"),
            "packing_group": get_text(section, "PackingGroup/PackingGroupImdg"),
            "environmental_hazards": get_text(
                section, "EnvironmentalHazards/Imdg/EnvironmHazardAccordImdg/FullText"
            ),
            "special_provisions": get_text(imdg_other_node, "ImdgSpecialProvisions")
            or "223 | 274",
            "limited_quantity": get_text(imdg_other_node, "ImdgLimitedQty"),
            "excepted_quantities": get_text(imdg_other_node, "ImdgExceptedQty"),
            "ems_code": get_text(imdg_other_node, "ImdgEmsCode"),
        }
        icao_iata_node = self._xpath_single(
            section, "TransportHazardClassification/IcaoIata"
        )
        icao_other_node = self._xpath_single(
            section, "OtherTransportInformation/IcaoIataOtherInformation"
        )
        # TODO: hardcoded - fallback values ('3', 'A3 | A180', 'Y344', 'E1') should come from XML/PDF extraction
        air_data = {
            "un_number": get_text(section, "UnNo/UnNoIcao"),
            "shipping_name": _get_shipping_name(
                self._xpath_single(section, "ProperShippingName/Icao"),
                "ProperShippingNameEnglishIcao/FullText",
                ["DangerReleasingSubstanceEnglishIcao/FullText"],
            ),
            "transport_class": get_text(icao_iata_node, "ClassIcaoIata"),
            "packing_group": get_text(section, "PackingGroup/PackingGroupIcaoIata"),
            "environmental_hazards": get_text(
                section, "EnvironmentalHazards/EnvironmHazardAccordIcaoIata/FullText"
            ),
            "special_provisions": get_text(
                icao_other_node, "IcaoIataSpecialProvisions"
            ),
            "limited_quantity": get_text(icao_other_node, "IcaoIataLimitedQty")
            or "Y344",
            "excepted_quantities": get_text(icao_other_node, "IcaoIataExemptedQty"),
        }
        return {
            "land": land_data,
            "inland": inland_data,
            "sea": sea_data,
            "air": air_data,
            "bulk_transport": get_text(section, "TransportInBulk") or "No data available",
            "special_precautions": get_all_text_from_nodes(section, "SpecialPrecautionsForUser") or "No data available",
            "transport_icons": self._get_transport_icons_from_classes([
                land_data.get("transport_class"),
                inland_data.get("transport_class"),
                sea_data.get("transport_class"),
                air_data.get("transport_class")
            ])
        }

    def _parse_section_15(self, section: etree._Element) -> Dict:
        # Get the Germany-specific national legislation node
        national_legislation_node = self._xpath_single(
            section, "NationalLegislation/NationalLegislationGermany"
        )

        # Extract specific, known fields
        restrictions = get_all_text_from_nodes(
            national_legislation_node, "RestrictionsOfOccupation"
        )
        wgk = get_text(national_legislation_node, "WaterHazardClass/Class")
        storage_class = get_text(national_legislation_node, "StorageClass")
        giscode = get_text(national_legislation_node, "GisCode")

        # Collect any other 'AdditionalInformation' fields
        additional_info = []
        if national_legislation_node is not None:
            for elem in national_legislation_node.xpath(
                './/*[local-name()="AdditionalInformation"]/*[local-name()="FullText"]'
            ):
                if elem.text:
                    additional_info.append(elem.text.strip())

        return {
            "eu_legislation": get_text(
                section, "SpecificProvisionsRelatedToProduct/EuLegislation"
            ) or "No data available",
            "restrictions": restrictions or "No data available",
            "wgk": wgk or "No data available",
            "storage_class": storage_class or "No data available",
            "giscode": giscode or "No data available",
            "additional_info": additional_info,
            "chemical_safety_assessment": get_all_text_from_nodes(section, "ChemicalSafetyAssessment") or "No data available",
        }

    def _parse_section_16(self, section: etree._Element) -> Dict:
        abbreviations = []
        for abbr in section.xpath('.//*[local-name()="Abbreviation"]'):
            abbreviations.append(
                {
                    "short": get_text(abbr, "AbbreviationShort"),
                    "long": get_text(abbr, "AbbreviationLong"),
                }
            )
        return {
            "other_information": {
                "indication_of_changes": get_all_texts(
                    section, "IndicationOfChanges/FullText"
                ),
                "abbreviations": abbreviations,
                "abbreviations_source_note": get_text(
                    section, "AbbreviationSourceNote/FullText"
                ),
                "literature_references": get_all_text_from_nodes(
                    section, "LiteratureReferencesAndDataSources/FullText"
                ),
                "training_advice": get_all_text_from_nodes(
                    section, "TrainingAdvice/FullText"
                ),
                "additional_info_lines": get_all_texts(
                    section, "OtherInformation/FullText"
                ),
            }
        }
        
    def _get_ppe_icons_from_text(self, eye: str, skin: str, resp: str) -> list:
        """
        Determines the appropriate PPE icons based on the text descriptions
        for eye, skin, and respiratory protection.
        """
        icons = []
        
        # Eye protection
        if eye and any(word in str(eye).lower() for word in ['eye', 'face', 'goggles', 'glasses', 'brille', 'augenschutz']):
            icons.append('M004_Augenschutz-benutzen.jpg')
            
        # Skin/Hand protection
        if skin and any(word in str(skin).lower() for word in ['skin', 'hand', 'glove', 'handschutz', 'handschuhe']):
            icons.append('M009_Handschutz_benutzen.jpg')
            
        # Body protection (often bundled with skin/hands in the text)
        if skin and any(word in str(skin).lower() for word in ['body', 'clothing', 'schutzkleidung', 'schutzanzug']):
            icons.append('M010_Schutzkleidung-benutzen.jpg')
            
        # Respiratory protection
        if resp and any(word in str(resp).lower() for word in ['respirator', 'mask', 'breathing', 'atemschutz']):
            icons.append('M017_Atemschutz-benutzen.jpg')
            
        import base64
        from pathlib import Path
        
        b64_icons = []
        base_dir = Path(__file__).parent
        for icon in icons:
            icon_path = base_dir / "symbole" / icon
            if icon_path.exists():
                with open(icon_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    b64_icons.append(f"data:image/jpeg;base64,{b64}")
        return b64_icons
        
    def _get_transport_icons_from_classes(self, classes: list) -> list:
        """
        Maps transport classes to ADR diamonds or fallback GHS symbols.
        Returns a list of Base64 encoded images.
        """
        import base64
        from pathlib import Path
        
        b64_icons = []
        base_dir = Path(__file__).parent / "symbole"
        if not base_dir.exists():
            return []
            
        processed_classes = set()
        
        for tc in classes:
            if not tc or str(tc).strip() == "" or str(tc) == "No data available":
                continue
                
            tc = str(tc).strip()
            if tc in processed_classes:
                continue
            processed_classes.add(tc)
            
            found_icon = False
            
            # 1. Versuche ein explizites ADR/Transport-Piktogramm im Ordner zu finden
            possible_names = [
                f"ADR_{tc}.png", f"ADR_{tc}.jpg", f"ADR_{tc}.gif",
                f"Class_{tc}.png", f"Class_{tc}.jpg", f"Class_{tc}.gif",
                f"Klasse_{tc}.png", f"Klasse_{tc}.jpg", f"Klasse_{tc}.gif",
                f"Transport_{tc}.png", f"Transport_{tc}.jpg", f"Transport_{tc}.gif"
            ]
            
            for name in possible_names:
                icon_path = base_dir / name
                if icon_path.exists():
                    with open(icon_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                        ext = name.split('.')[-1].lower()
                        mime = "image/jpeg" if ext == "jpg" else f"image/{ext}"
                        b64_icons.append(f"data:{mime};base64,{b64}")
                    found_icon = True
                    break
                    
            # 2. Automatischer Fallback auf die hochwertigen GHS-Symbole (Klasse -> GHS-Entsprechung)
            if not found_icon:
                class_to_ghs = {
                    '1': 'GHS_01_gr.gif', '2.1': 'GHS_02_gr.gif', '2.2': 'GHS_04_gr.gif',
                    '2.3': 'GHS_06_gr.gif', '3': 'GHS_02_gr.gif', '4.1': 'GHS_02_gr.gif',
                    '4.2': 'GHS_02_gr.gif', '4.3': 'GHS_02_gr.gif', '5.1': 'GHS_03_gr.gif',
                    '5.2': 'GHS_03_gr.gif', '6.1': 'GHS_06_gr.gif', '6.2': 'GHS_06_gr.gif',
                    '8': 'GHS_05_gr.gif', '9': 'GHS_09_gr.gif'
                }
                ghs_icon = class_to_ghs.get(tc)
                if not ghs_icon and tc[0] in class_to_ghs:
                    ghs_icon = class_to_ghs.get(tc[0])
                    
                if ghs_icon:
                    ghs_path = base_dir / ghs_icon
                    if ghs_path.exists():
                        with open(ghs_path, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode("utf-8")
                            b64_icons.append(f"data:image/gif;base64,{b64}")
                            
        # Duplikate filtern und zurückgeben
        return list(dict.fromkeys(b64_icons))


def parse_sds_xml(xml_path: str, pdf_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Factory function to instantiate and run the parser.

    Args:
        xml_path: Path to the SDScom XML file.
        pdf_path: Optional path to the companion PDF file. When provided,
                  any empty/missing fields in the XML data are filled from
                  the PDF (XML always takes precedence).
    """
    try:
        logger.info(f"Starting to parse XML: {xml_path}")
        parser = NewSDScomParser(xml_path, pdf_path=pdf_path)
        result = parser.parse()
        logger.info(f"Parsing completed successfully")
        return result
    except Exception as e:
        logger.error(f"Fatal error during XML parsing: {e}", exc_info=True)
        return {}


if __name__ == "__main__":
    import os

    xml_file = "Sdb_EU-REACH_MycoplasmaOff™_15-5000,15-1000,15-0050_V5_en_DE.xml"
    if os.path.exists(xml_file):
        parsed_data = parse_sds_xml(xml_file)
        if parsed_data:
            import json

            with open("parsed_sds_data.json", "w", encoding="utf-8") as f:
                json.dump(parsed_data, f, indent=2, ensure_ascii=False)
            print("Parsing successful. Data saved to parsed_sds_data.json")
        else:
            print("Parsing failed.")
    else:
        print(f"Test file not found: {xml_file}")
