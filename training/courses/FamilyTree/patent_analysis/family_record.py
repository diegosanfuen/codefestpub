from collections import Counter, defaultdict
import os
from typing import Optional, Dict, Tuple, List, Set
import xml.etree.ElementTree as ET
import pandas as pd
from epo.tipdata.ops import OPSClient, models, exceptions
import re
from IPython.display import display
from patent_analysis.helpers import convert_japanese_priority_number, sort_orap
from pprint import pprint
import logging
#  logging.basicConfig(level=logging.DEBUG)
        
# Set display options for pandas
pd.set_option('display.max_rows', None)  # Display all rows
pd.set_option('display.max_columns', None)  # Display all columns
pd.set_option('display.width', None)  # Avoid line wrapping
pd.set_option('display.max_colwidth', None)  # Show full column content

class FamilyRecord:
    """
    Represents family record in the European Patent Office (EPO) database.
    Provides methods to fetch, parse, and process patent family data.
    """
    _print_executed = False
    
    # Put more fundamental/lower-level methods earlier in the class definition:
    def __init__(self, reference_type: str, doc_number: str, country: Optional[str] = None, kind: Optional[str] = None, constituents: Optional[str] = None, countrySelection=None, output_type: Optional[str] = None, ):  
        """
        Initialize the FamilyRecord object.
        
        Args:
        - reference_type (str): The type of reference (e.g., 'publication', 'application').
        - doc_number (str): The document number.
        - country (str): The country code (e.g., 'EP' for Europe).
        - kind (Optional[str]): The kind code (e.g., 'A' for application, 'B' for publication).
        - constituents (Optional[str]): Constituents for the OPSClient.
        - countrySelection (Optional[List[str]]): List of countries for filtering.
        - output_type (Optional[str]): Output type for the OPSClient.        
        """        
        self.client: OPSClient = OPSClient(key=os.getenv("OPS_KEY"), secret=os.getenv("OPS_SECRET"))
        self.reference_type: str = reference_type
        self.doc_number: str = doc_number        
        self.source_doc_number: Optional[str] = self.compute_source_doc_number(doc_number, country, kind)
        self.country: Optional[str] = country
        self.kind: Optional[str] = kind
        self.constituents: Optional[List[str]] = ["legal", "biblio"] if constituents is None else (
            [constituents] if isinstance(constituents, str) else constituents
        )
        self.countrySelection = countrySelection if isinstance(countrySelection, list) else [countrySelection]
        self.output_type: str = output_type
        self.ccw_to_wo_mapping = {}
        self.familyRoot = None
        self.xml_tree = None
        self.data = {}  # Initialize the data attribute
        self.pd = pd  # Assign pandas to self.pd
        self.df, self.DropdownCC = self._initialize_dataframe()
        if self.df is not None:
            self.df['source_doc_number'] = self.source_doc_number
        else:
            print("Error: DataFrame is empty or failed to initialize.")
        
    def compute_source_doc_number(self, doc_number: str, country: str, kind: Optional[str]) -> str:
        """
        Compute the source document number by concatenating country code, document number, and kind code.
        
        Args:
        - doc_number (str): The document number.
        - country (str): The country code.
        - kind (Optional[str]): The kind code.

        Returns:
        - str: The computed source document number.
        """        
        # source_doc_number = f"{country}{doc_number}"  # Start with concatenating country code and doc_number
        source_doc_number = f"{country or ''}{doc_number}"  # Start with concatenating country code and doc_number
        if kind:
            # source_doc_number = f"{country}{doc_number}{kind}"
            source_doc_number = f"{source_doc_number}{kind}"
        return source_doc_number

    def _fetch_xml_tree(self, reference_type: str, doc_number: str, country: str, kind: Optional[str] = None, constituents: Optional[str] = None, output_type: Optional[str] = None) -> Optional[str]:
        """_fetch_xml_tree
        Fetch the XML data from the EPO database.
        
        Args:
        - reference_type (str): The type of reference.
        - doc_number (str): The document number.
        - country (str): The country code.
        - kind (Optional[str]): The kind code.
        - constituents (Optional[List[str]]): List of constituents for the OPSClient.
        - output_type (Optional[str]): Output type for the OPSClient.
        
        Returns:
        - Optional[str]: The fetched XML data as a string if successful, None otherwise.
        """        
        try:
            input_model = models.Docdb(doc_number, country, kind) if kind else models.Epodoc(f"{country}{doc_number}")
            # print("reference_type:", reference_type)
            # print("input_model, doc_number, country, kind:", input_model, doc_number, country, kind)
            # print("constituents:", constituents)
            # print("output_type:", output_type)
            self.xml_tree = self.client.family(reference_type=reference_type, input=input_model, constituents=constituents, output_type=output_type)
            return self.xml_tree
        except exceptions.HTTPError as e:
            print(f"HTTPError: {e}")
            return None

    # This is a core data-fetching method. It should come before methods that depend on the XML data.
    def get_family_root(self) -> Optional[ET.Element]:
        """
        Get the root element of the family XML tree.

        Returns:
        - Optional[ET.Element]: The root element if XML tree is parsed successfully, None otherwise.
        """        
        if self.xml_tree is None:
            print("Error: self.xml_tree is not initialized.")
            return None
        return ET.fromstring(self.xml_tree)

    def _parse_xml(self) -> Optional[ET.Element]:
        """
        Parses XML from self.xml_tree and returns the root element.

        Returns:
        - Optional[ET.Element]: The root element if XML tree is parsed successfully, None otherwise.
        """        
        if self.xml_tree is None:
            print("Error: self.xml_tree is None.")
            return None
        try:
            # print("self.xml_tree:", self.xml_tree)
            return ET.fromstring(self.xml_tree)  # Parse the XML string
        except ET.ParseError as e:
            print(f"XML parsing failed: {e}")
            return None

    def _get_namespace_map(self) -> Dict[str, str]:
        """
        Returns the namespace map for XML parsing.

        Returns:
        - Dict[str, str]: The namespace map.
        """
        return {
            'ops': 'http://ops.epo.org',
            'exchange': 'http://www.epo.org/exchange'
        }
        
    # def get_ns_prefix(self, tag, nsmap):
    def get_ns_prefix(self, tag: str, nsmap: Dict[str, str]) -> str:
        """
        Resolves the namespace prefix and builds a fully qualified tag.

        Args:
            tag (str): The tag with a namespace prefix (e.g., "ops:family-member").
            nsmap (dict): A dictionary mapping namespace prefixes to their URIs.

        Returns:
            str: The fully qualified tag with the namespace URI.
    
        Raises:
            ValueError: If the tag does not contain a prefix or the prefix is not found in nsmap.
        """
        parts = tag.split(':')
        if len(parts) != 2:
            raise ValueError(f"Invalid tag format: {tag}. Expected format 'prefix:tag'.")
    
        prefix, local_name = parts
        namespace_uri = nsmap.get(prefix)
        if not namespace_uri:
            raise ValueError(f"Namespace prefix '{prefix}' not found in nsmap.")
    
        return f"{{{namespace_uri}}}{local_name}"

    # Utility for XML parsing. Parses the XML tree and returns a list of family members.
    # def _extract_family_members(self):
    def _extract_family_members(self) -> List[ET.Element]:
        """
        Extracts family members from the XML tree.

        Returns:
        - List[ET.Element]: List of family member elements.
        """
        return self.familyRoot.findall(".//{http://ops.epo.org}family-member")

    def _parse_application_data(self, family_member, nsmap) -> Tuple[str, Dict]:
        """
        Extracts application details such as country, kind, number, and date.

        Args:
        - family_member (ET.Element): The family member element.
        - nsmap (Dict[str, str]): The namespace map.

        Returns:
        - Tuple[Optional[str], Dict[str, Any], Optional[str]]: Application number, application data, and kind text.
        """
        app_number_full = None
        app_data = {}

        for application_reference in family_member.findall(f".//{self.get_ns_prefix('exchange:application-reference', nsmap)}"):
            app_doc_number = application_reference.find(f".//{self.get_ns_prefix('exchange:doc-number', nsmap)}")
            app_country = application_reference.find(f".//{self.get_ns_prefix('exchange:country', nsmap)}")
            app_kind = application_reference.find(f".//{self.get_ns_prefix('exchange:kind', nsmap)}")
            app_date = application_reference.find(f".//{self.get_ns_prefix('exchange:date', nsmap)}")

            app_number = app_doc_number.text if app_doc_number is not None else None
            app_country_text = app_country.text if app_country is not None else 'Unknown'
            app_kind_text = app_kind.text if app_kind is not None else 'Unknown'
            app_date_text = app_date.text if app_date is not None else None
            app_number_full = f"{app_country_text}{app_number}"

            if app_number_full.startswith('EP'):
                year_prefix = '19' if int(app_number_full[2:4]) > 50 else '20'
                app_number_full = f"EP{year_prefix}{app_number_full[2:11]}"

            accession_number = app_number_full
            
            # Handle WO (PCT) mappings
            if app_kind_text == 'W' or app_country_text == 'WO':
                accession_number = f"{app_country_text}{app_kind_text}{app_number}"
                if int(app_number[:2]) > 50:
                    year_prefix = '19' 
                    app_number_full = f"WO19{app_number[:2]}{app_country_text}{app_number[2:]}"
                else:
                    year_prefix = app_number[:4]
                    serial_number = app_number[4:].lstrip('0')
                    app_number_full = f"WO{year_prefix}{app_country_text}{serial_number}"
                self.ccw_to_wo_mapping[accession_number] = (app_number_full, app_date_text)

            # Include additional fields
            app_data = {
                'accession_number': accession_number,
                'app_number': app_number_full,
                'app_country': app_country_text,
                'app_kind': app_kind_text,
                'app_date': app_date_text,
                'priority_numbers': [],   # Placeholder for priority numbers
                'orap': {},               # Placeholder for other application references
                'priority_dates': {},     # Placeholder for priority dates
                'pub_number': '',
                'pub_country': '',
                'pub_kind': '',
                'pub_date': '',
                'legal_events': []
            }

        return app_number_full, app_data, app_kind_text, app_country_text

    def _parse_publication_data(self, index, family_member, nsmap, data, app_number_full, app_data, country_codes):
        """
        Parse and process publication data from the family member element.

        Args:
        - family_member (ET.Element): The family member element.
        - nsmap (Dict[str, str]): The namespace map.
        - data (Dict[str, Any]): The data dictionary to update with parsed information.
        - app_number_full (str): The full application number.
        - app_data (Dict[str, Any]): The application data dictionary to update.
        - country_codes (Set[str]): A set to track country codes.
        """        
        pub_data = {
            'pub_number': None,
            'pub_country': None,
            'pub_kind': None,
            'pub_date': None
        }
    
        for publication_reference in family_member.findall(f".//{self.get_ns_prefix('exchange:publication-reference', nsmap)}"):
            pub_attrs = {
                "pub_number": publication_reference.find(f".//{self.get_ns_prefix('exchange:doc-number', nsmap)}"),
                "pub_country": publication_reference.find(f".//{self.get_ns_prefix('exchange:country', nsmap)}"),
                "pub_kind": publication_reference.find(f".//{self.get_ns_prefix('exchange:kind', nsmap)}"),
                "pub_date": publication_reference.find(f".//{self.get_ns_prefix('exchange:date', nsmap)}")
            }
        
            # Extract text values, ensuring defaults where necessary
            pub_data = {key: (elem.text if elem is not None else None) for key, elem in pub_attrs.items()}

            pub_data['pub_country'] = pub_data['pub_country'] or 'Unknown'
            
            # print("pub_data['pub_number'][:2]:", pub_data['pub_number'][:2], pub_data['pub_country'])            
            if pub_data['pub_number'][:2] == 'WO' and pub_data['pub_country'] != 'WO':
                pub_data['pub_country'] = 'WO'
                
            # print("pub_data['pub_number'], pub_data['pub_country']:", pub_data['pub_number'], pub_data['pub_country'])
            
            if pub_data['pub_number'] and str(pub_data['pub_number']).isdigit():
                pub_data['pub_number'] = f"{pub_data['pub_country']}{pub_data['pub_number']}"

        
            if app_number_full in data:
                # Update pub_data only with non-empty values
                for key, value in pub_data.items():
                    if value:
                       pub_data[key] = value
                        
                # Update app_data directly
                app_data.update({
                    'pub_number': pub_data.get('pub_number', None),
                    'pub_country': pub_data.get('pub_country', None)
                })

                # app_data.update({k: v for k, v in pub_data.items() if v})  # Update only non-empty values
                country_codes.add(pub_data['pub_country'])
            
        return pub_data
    
    # Sorting function
    def custom_sort_key(self, item):
        # print("myItem:", item)
        if len(item) > 2 and item[2] == 'W':  # Check if 'W' is in the third position
            return (0, item)  # Highest priority
        elif 'EP' in item:
            return (1, item)  # Second priority
        else:
            return (2, item)  # Lowest priority
            
    def _parse_priority_claims(self, index, family_member, nsmap, data, app_number_full, app_data, app_kind_text, app_country_text, pub_data):
        """
        Extracts application details such as country, kind, number, and date.

        Args:
        - family_member (ET.Element): The family member element.
        - nsmap (Dict[str, str]): The namespace map.

        Returns:
        - Tuple[Optional[str], Dict[str, Any], Optional[str]]: Application number, application data, and kind text.
        """
        processed_prios = set()
        for priority_claim in family_member.findall(f".//{self.get_ns_prefix('exchange:priority-claim', nsmap)}"):
            elements = { 
                key: priority_claim.find(f".//{self.get_ns_prefix(f'exchange:{key}', nsmap)}")
                for key in ['doc-number', 'country', 'kind', 'date']
            }

            if elements['doc-number'] is not None:
                priority_doc_number = elements['doc-number'].text                
                priority_country = elements['country'].text if elements['country'] is not None else 'Unknown'
                priority_kind = elements['kind'].text if elements['kind'] is not None else ''
                priority_date = elements['date'].text if elements['date'] is not None else ''

                priority_doc_number_full = f"{priority_country}{priority_doc_number}"
                if priority_doc_number_full.startswith('EP'):
                    year_prefix = '19' if int(priority_doc_number_full[2:4]) > 50 else '20'
                    priority_doc_number_full = f"EP{year_prefix}{priority_doc_number_full[2:11]}"
                if priority_kind == 'W':
                    priority_doc_number_full = f"{priority_country}{priority_kind}{priority_doc_number}"
            
                priority_doc_number_full = convert_japanese_priority_number(priority_doc_number_full)               
                # print("priority_doc_number_full:", priority_doc_number_full)
                
                if app_number_full in data:
                    # Ensure 'priority_numbers' is a list and append to it
                    if not isinstance(app_data.get('priority_numbers'), list):
                        app_data['priority_numbers'] = []
                        
                    if 'orap' not in app_data:
                        app_data['orap'] = {}            
                    if 'priority_dates' not in app_data:
                        app_data['priority_dates'] = {}
                        
                    if (priority_doc_number_full not in app_data['priority_dates']) or (
                        priority_date and priority_date > app_data['priority_dates'][priority_doc_number_full]
                    ):
                        # Update the latest priority date
                        app_data['priority_dates'][priority_doc_number_full] = priority_date

                    # **Sort priority dates by date in ascending order**
                    app_data['priority_dates'] = dict(sorted(app_data['priority_dates'].items(), key=lambda x: x[1], reverse=True))

                    # # **Select the latest priority_doc_number_full**
                    # latest_priority_doc_number = next(iter(app_data['priority_dates']), None)  # Get the first key (latest date)

                    # **Sort priority dates by date in descending order (latest first)**
                    sorted_priority_dates = sorted(app_data['priority_dates'].items(), key=lambda x: x[1], reverse=True)

                    # print("app_number_full:", app_number_full)
                    # print("app_data['priority_dates']:", app_data['priority_dates'])

                    if priority_doc_number_full not in processed_prios and priority_doc_number_full not in app_data['orap']:
                        # print("output index + app_number_full + priority_doc_number_full:", index, app_number_full, priority_doc_number_full)
                        # print("app_kind_text, app_country_text, priority_country:", app_kind_text, app_country_text, priority_country)
                        if app_kind_text == 'W' or priority_country in ['EP'] or (  # == 'EP'
                            len(priority_doc_number_full) >= 3 and priority_doc_number_full[2] == 'W'
                        ) or 'WO' in pub_data['pub_number']:
                            if priority_doc_number_full not in app_data['priority_numbers']:
                                app_data['priority_numbers'].append(priority_doc_number_full)
                                
                            if app_kind_text != 'W' and (priority_country in ['EP'] or (    # == 'EP'
                                len(priority_doc_number_full) >= 3 and priority_doc_number_full[2] == 'W'
                            ) or 'WO' in pub_data['pub_number']):
                                # **Select the latest priority_doc_number_full**
                                if sorted_priority_dates:                                      
                                    latest_priority_doc_number = sorted_priority_dates[0][0]  # Get the key with the latest date
                                    app_data['orap'] = [latest_priority_doc_number]  # Assign the latest priority to 'orap'
                                    # print("in first condition : index, app_number_full + priority_doc_number_full, pub_data['pub_number']:", index, app_number_full, priority_doc_number_full, pub_data['pub_number'])
                                    # print("Selected latest priority_doc_number_full for 'orap':", app_data.get('orap'))
                                    # app_data['orap'] = priority_doc_number_full
                                    processed_prios.add(latest_priority_doc_number)
                                
                            elif app_kind_text == 'W' :                           
                                # print("0. app_number_full, priority_doc_number_full:", app_number_full, priority_doc_number_full)
                                # app_data['orap'] = [priority_doc_number_full]
                                # processed_prios.add(priority_doc_number_full)
                                app_data['orap'] = [app_number_full]
                                processed_prios.add(app_number_full)
                                
                        elif app_country_text != 'EP' and app_number_full != priority_doc_number_full and priority_country != 'EP':
                            # print("out: app_number_full + priority_doc_number_full:", app_number_full, priority_doc_number_full)
                            # print("app_country_text, priority_country:", app_country_text, priority_country)                       
                            if not app_data['priority_numbers'] and not app_data['orap']:
                                # print("in second condition :")
                                # print("1. app_data['priority_numbers']", app_data['priority_numbers'])
                                # print("1. app_data['orap']:", app_data['orap'])
                                processed_prios.add(priority_doc_number_full)                                
                                if priority_doc_number_full not in app_data['priority_numbers']:
                                    app_data['priority_numbers'].append(priority_doc_number_full)
                                if not app_data['orap']:
                                    app_data['orap'] = [priority_doc_number_full]
                            #     print("2. app_data['priority_numbers']", app_data['priority_numbers'])
                            #     print("2. app_data['orap']:", app_data['orap'])
                            # else:
                            #     print("3. app_data['priority_numbers']", app_data['priority_numbers'])
                            #     print("3. app_data['orap']:", app_data['orap'])                       
                        # if 'WO' in pub_data['pub_number']: # if app_kind_text == 'W' or 'W' in priority_country or priority_doc_number_full[2] == 'W' or 'WO' in pub_data['pub_number']:
                        #     print("index + app_number_full + priority_doc_number_full, pub_data['pub_number'], pub_data['pub_country']:", index, app_number_full, priority_doc_number_full, pub_data['pub_number'], pub_data['pub_country'])
                        #     print("app_kind_text, app_country_text, priority_country:", app_kind_text, app_country_text, priority_country)
    
                    # print("End of loop")
                    # print()

    def _parse_legal_events(self, index, family_member, nsmap, data, app_number_full, app_data): 
        """
        Parse and process legal events from the family member element.

        Args:
        - family_member (ET.Element): The family member element.
        - nsmap (Dict[str, str]): The namespace map.
        - data (Dict[str, Any]): The data dictionary to update with parsed information.
        - app_number_full (str): The full application number.
        - app_data (Dict[str, Any]): The application data dictionary to update.
        """        
        for legal_event in family_member.findall(f".//{self.get_ns_prefix('ops:legal', nsmap)}"):
            legal_event_data = {
                'legal_event_code': legal_event.attrib.get('code', ''),
                'legal_event_desc': legal_event.attrib.get('desc', ''),
                'legal_event_date_migr': legal_event.attrib.get('dateMigr', ''),
                'legal_event_infl': legal_event.attrib.get('infl', ''),
                'legal_event_texts': [pre.text.strip() for pre in legal_event.findall('.//{http://ops.epo.org}pre') if pre.text],
                'nested_data': None  # Ensures 'nested_data' exists
            }
            if app_number_full in data:
                # print("legal_event_data:", legal_event_data)
                app_data['legal_events'].append(legal_event_data)

    def _process_family_member(self, index, family_member: ET.Element, nsmap: Dict[str, str], data: Dict, country_codes: Set[str]):
        """
        Parses and processes data for a single family member.

        Args:
        - family_member (ET.Element): The family member element.
        - nsmap (Dict[str, str]): The namespace map.
        - data (Dict[str, Any]): The data dictionary to update with parsed information.
        - country_codes (Set[str]): A set to track country codes.
        """
        app_number_full, app_data, app_kind_text, app_country_text = self._extract_application_data(family_member, nsmap)
    
        if not app_number_full:
            return  # Skip processing if no valid application data

        data[app_number_full] = app_data
        country_codes.add(app_data['app_country'])
        
        if isinstance(data[app_number_full]['priority_numbers'], list):
            data[app_number_full]['priority_numbers'].extend(app_data.get('priority_numbers', []))
        else:
            data[app_number_full]['priority_numbers'].update(app_data.get('priority_numbers', set()))

        if isinstance(data[app_number_full]['orap'], list):
            data[app_number_full]['orap'].extend(app_data.get('orap', []))
        else:
            data[app_number_full]['orap'].update(app_data.get('orap', set()))

        pub_data = self._parse_publication_data(index, family_member, nsmap, data, app_number_full, app_data, country_codes)
        
        self._parse_priority_claims(index, family_member, nsmap, data, app_number_full, app_data, app_kind_text, app_country_text, pub_data)
        self._parse_legal_events(index, family_member, nsmap, data, app_number_full, app_data)

    def _add_missing_countries(self, data: Dict[str, Dict], country_codes: Set[str]):
        """
        Ensures all selected countries are represented in the data.

        Args:
        - data (Dict[str, Dict[str, Any]]): The data dictionary to update with missing countries.
        - country_codes (Set[str]): A set of existing country codes.
        """
        missing_countries = set(self.countrySelection) - country_codes
        for country in missing_countries:
            data[f"{country or 'Unknown'}0000000"] = {
                'accession_number': '',
                'app_number': f"{country or 'Unknown'}0000000",
                'app_country': country,
                'app_kind': None,
                'app_date': None,
                'priority_numbers': [],
                'orap': {},
                'orap_history': [],
                'priority_dates': {},
                'legal_events': [],
                'pub_number': None,
                'pub_country': None,
                'pub_kind': None
            }

    def _create_dataframe(self, data: Dict[str, Dict]) -> pd.DataFrame:
        """Flattens extracted data into a pandas DataFrame."""
        flattened_data = [
            {
                **value,
                'priority_numbers': sorted(value['priority_numbers'], key=self.custom_sort_key),
                'orap': sorted(value['orap'], key=self.custom_sort_key),
                'legal_events': [
                    {
                        'code': event.get('legal_event_code', ''),
                        'desc': event.get('legal_event_desc', ''),
                        'dateMigr': event.get('legal_event_date_migr', ''),
                        'infl': event.get('legal_event_infl', ''),
                        'texts': ' | '.join(event.get('legal_event_texts', [])),
                        'nested_data': event.get('nested_data', None)
                    }
                    for event in value['legal_events']
                ],
                'pub_number': value.get('pub_number', None),
                'pub_country': value.get('pub_country', None),
                'pub_kind': value.get('pub_kind', None)
            }
            for value in data.values()
        ]
    
        df = pd.DataFrame(flattened_data)
        df = df[df['app_number'] != "Unknown0000000"]  # Remove placeholders
    
        if df.empty:
            print("Warning: DataFrame is empty after filtering out 'Unknown0000000'.")
    
        return df
    
    def _parse_xml_to_dataframe(self) -> Optional[pd.DataFrame]:
        """Parses the XML, processes family members, and returns a DataFrame."""
        self.familyRoot = self._parse_xml()
        if self.familyRoot is None:
            return None, []

        nsmap = self._get_namespace_map()
        data = defaultdict(lambda: {
            'accession_number': '',
            'app_number': '',
            'app_country': '',
            'app_kind': None,
            'app_date': None,
            'pub_number': '',
            'pub_country': '',
            'pub_kind': '',            
            'priority_numbers': [],
            'orap': {},
            'orap_history': [],
            'priority_dates': {},
            'legal_events': []
        })
        country_codes = set()
    
        family_members = self._get_family_members()
        if not FamilyRecord._print_executed:
            print()
            print(f"Extracted {len(family_members)} family members in the parsed XML.")

        for index, family_member in enumerate(family_members):
            self._process_family_member(index, family_member, nsmap, data, country_codes)

        self._add_missing_countries(data, country_codes)
        df = self._create_dataframe(data)
    
        return df, sorted(country_codes)

    def _initialize_dataframe(self, country: Optional[str] = None, xml_tree: Optional[str] = None, ) -> pd.DataFrame:
        country = country if country else self.country
        try:
            self.xml_tree = self._fetch_xml_tree(self.reference_type, self.doc_number, self.country, self.kind, self.constituents, self.output_type)
            if self.xml_tree is None:
                return pd.DataFrame(), []
            # pprint(self.xml_tree[:20000])
            self.df, self.dropdown_cc = self._parse_xml_to_dataframe()
            
            # Populate the `data` attribute based on `self.df`
            if self.df is not None and not self.df.empty:
                # Populate the `data` attribute based on `df`
                for _, row in self.df.iterrows():
                    app_number_full = row['app_number']
                    if app_number_full not in self.data:
                        self.data[app_number_full] = {
                            'orap': {},
                            'priority_numbers': [],
                            'priority_dates': {}
                        }
                if not FamilyRecord._print_executed:                        
                    print(f"Extracted {len(self.df)} family members in the parsed dataframe.")
                    print()
                    FamilyRecord._print_executed = True
            else:
                print("Error: DataFrame is empty after parsing XML.")
                return self.pd.DataFrame(), []

            # Debugging for the environment
            try:
                from IPython.display import display
                # print("_initialize_dataframe:")
                # display(self.df)  # to use in priority for self.df display
            except ImportError:
                print(self.df.head())  # Fallback for non-Jupyter environments

            return self.df, self.dropdown_cc
        except Exception as e:
            print(f"Error initializing DataFrame: {e}")
            import traceback
            traceback.print_exc()  # This will print the full traceback            
            return self.pd.DataFrame(), []
            
    def _get_family_members(self) -> List[ET.Element]:
        """Extracts and returns a list of family members from the parsed XML."""
        return list(self._extract_family_members())

    def _extract_application_data(self, family_member: ET.Element, nsmap: Dict[str, str]) -> Tuple[Optional[str], Dict, Optional[str]]:
        """Extracts application data and returns a tuple (app_number_full, app_data, app_kind_text)."""
        app_number_full, app_data, app_kind_text, app_country_text = self._parse_application_data(family_member, nsmap)
    
        if not app_number_full:
            print("Skipping family member: No app_number_full")
            return None, {}, None
    
        app_data['app_country'] = app_data.get('app_country', 'Unknown')  # Ensure app_country is set  
        return app_number_full, app_data, app_kind_text, app_country_text

    def get_filtered_application_numbers(self, additional_countries: Optional[str] = None) -> Optional[pd.DataFrame]:
        if self.df is None:
            return None

        if 'app_country' not in self.df.columns:
            print("Column 'app_country' is missing from the DataFrame.")
            return pd.DataFrame()  # or handle appropriately
            
        if 'pub_country' not in self.df.columns:
            self.df['pub_country'] = None  # or pd.NA or ''

        additional_countries = additional_countries or []  # Ensure it's a list
        if isinstance(additional_countries, str):
            additional_countries = [additional_countries]
        
        # Define region-based country groups
        country_groups = {
            "europe": [
                'AL', 'AT', 'BE', 'BG', 'CH', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GR', 'HR', 'HU', 'IE', 
                'IS', 'IT', 'LI', 'LT', 'LU', 'LV', 'MC', 'MT', 'NL', 'NO', 'PL', 'PT', 'RO', 'RS', 'SE', 'SI', 'SK', 'SM', 
                'TR', 'MK', 'BY', 'MD', 'RU', 'UA'
            ],
            "asia": [
                'JP', 'CN', 'KR', 'TW', 'HK', 'MO', 'SG', 'TH', 'MY', 'PH', 'VN', 'ID', 'BN', 'KH', 'LA', 'MM', 'IN', 'PK', 
                'BD', 'LK', 'NP', 'BT', 'MV', 'KZ', 'UZ', 'KG', 'TJ', 'TM', 'AE', 'SA', 'IL', 'TR', 'IR', 'QA', 'KW', 'BH', 
                'OM', 'JO', 'LB', 'SY', 'YE', 'IQ', 'PS', 'AU', 'NZ', 'PG', 'FJ'
            ],
            "americas": [
                'US', 'CA', 'MX', 'GT', 'BZ', 'SV', 'HN', 'NI', 'CR', 'PA', 'CU', 'DO', 'HT', 'JM', 'TT', 'BB', 'BS', 'LC', 
                'GD', 'KN', 'AG', 'VC', 'DM', 'BR', 'AR', 'CO', 'CL', 'PE', 'VE', 'EC', 'BO', 'PY', 'UY', 'GY', 'SR', 'GF'
            ],
            "africa": [
                'DZ', 'EG', 'LY', 'MA', 'SD', 'TN', 'BJ', 'BF', 'CV', 'CI', 'GH', 'GM', 'GN', 'GW', 'LR', 'ML', 'MR', 'NE', 
                'NG', 'SN', 'SL', 'TG', 'AO', 'CM', 'CF', 'TD', 'CG', 'CD', 'GQ', 'GA', 'ST', 'BI', 'DJ', 'ER', 'ET', 'KE', 
                'MG', 'MW', 'MU', 'MZ', 'RW', 'SC', 'SO', 'TZ', 'UG', 'ZM', 'ZW', 'BW', 'LS', 'NA', 'SZ', 'ZA'
            ]
        }

        # Define filtering function
        def filter_by_region(region, exclude_second_w=False):
            condition = self.df['app_country'].isin(country_groups[region])
            if exclude_second_w:
                condition &= ~self.df['app_country'].str[1].eq('W')  # Exclude where 'W' is second letter
            condition &= (self.df['app_kind'] == 'W') | self.df['app_number'].str.contains(r'W$|W.*$', regex=True)
            return condition
        
        # Define main conditions
        condition_xx = condition_cn = condition_ep = condition_jp = condition_us = condition_wo = False
        
        # condition_cn = (self.df['app_country'] == 'CN') & (self.df['app_kind'] == 'A')        
        condition_ep = (self.df['app_country'] == 'EP') & (self.df['app_kind'] == 'A')
        # condition_jp = (self.df['app_country'] == 'JP') & (self.df['app_kind'] == 'A')
        # condition_us = (self.df['app_country'] == 'US') & (self.df['app_kind'] == 'A')
        condition_wo = ((self.df['app_country'] == 'WO') | (self.df['pub_country'] == 'WO')) & (self.df['app_kind'] == 'A')

        condition_europe = filter_by_region("europe")
        condition_asia = filter_by_region("asia", exclude_second_w=True)
        condition_americas = filter_by_region("americas")
        condition_african = filter_by_region("africa", exclude_second_w=True)

        # Handle user-defined country selection
        selected_countries = set(self.countrySelection or []) | set(additional_countries)
        # print("selected_countries:", selected_countries)
        condition_xx = self.df['app_country'].isin(selected_countries) if selected_countries else pd.Series(False, index=self.df.index)

        # Apply filters and return the filtered DataFrame
        filtered_df = self.df[
            condition_cn | condition_ep | condition_jp | condition_us | condition_wo | condition_xx # | condition_europe | condition_asia | condition_americas | condition_african
           # condition_cn | condition_ep | condition_jp | condition_us | condition_wo | condition_xx | condition_europe | condition_asia | condition_americas | condition_african
        ].copy()
                
        # Ensure 'orap' and 'orap_history' columns exist
        filtered_df.loc[:, 'orap'] = None
        filtered_df.loc[:, 'orap_history'] = None

        if not filtered_df.empty:
            filtered_df = filtered_df.apply(
                lambda row: sort_orap(row, self.ccw_to_wo_mapping, self.data), 
                    axis=1
            )

        return filtered_df  
    
    def process_fami_record(self, additional_countries: Optional[str] = None) -> None:
        """
        Process and display the family record.
        Retrieves filtered application numbers and prints them.

        Returns:
        - Optional[Tuple[pd.DataFrame, str]]: Tuple containing the filtered DataFrame and the source type, or None if no data.
        """

        # print("process_fami_record with additional_countries:", additional_countries)
        source = 'Epodoc' if self.kind is None else 'Docdb'

        # Use the method to get filtered publication numbers
        result = self.get_filtered_application_numbers(additional_countries)
        if result is not None and not result.empty:
            # print(f"Filtered Publication numbers (Source: {source}):")
            # display(result)
            return result, source
        else:
            print("DataFrame is empty. No data to process.")
            return None
