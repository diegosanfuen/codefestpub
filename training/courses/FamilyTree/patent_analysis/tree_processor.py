# patent_analysis/tree_processor.pyFamilyRecord

from collections import Counter
import os
import re
import io
import pandas as pd
from typing import List, Dict, Any
from epo.tipdata.ops import OPSClient, models, exceptions
import xml.etree.ElementTree as ET
from IPython.display import Markdown, display
from PIL import Image
import requests
from pprint import pprint
import logging
from datetime import datetime

class TreeProcessor:
    """
    The TreeProcessor class is designed to process a hierarchical tree of patent application data, 
    generate a text-based summary, and manage the interaction with the OPSClient API to retrieve detailed information about the patent family.
    The TreeProcessor class is responsible for writing results to a file, and handling different patent-related entities such as applications, 
    publications, and legal events. It uses the OPSClient to interact with the European Patent Office API.
    """
    def __init__(self, tree: Dict[str, Any], root: Dict[str, Any], initFlag: str, listAPs: List[str], listORAPs: List[str], df: pd.DataFrame, familyRoot):
        """
        Initialize a TreeProcessor instance with the necessary data structures and configurations.
        It checks for the correct structure of the tree and initializes several attributes, including setting up the file path for saving the tree output.

        Args:
            tree (dict): Tree structure containing patent data.
            root (dict): Root node of the tree.
            initFlag (str): A flag to indicate specific processing methods.
            listAPs (list): List of application identifiers.
            listORAPs (list): List of original application identifiers.
            df (pd.DataFrame): DataFrame containing relevant publication data.
            familyRoot: Additional family-related data.
        
        Raises:
            TypeError: If 'tree' is a list instead of a dictionary-like object.
            AttributeError: If the 'tree' object doesn't have a 'recInp' attribute.
        """           
        self.tree = tree  # A dictionary representing the tree structure.
        self.root = root  # A dictionary containing root elements of the tree.
        self.initFlag = initFlag  # A string used to control which data is processed.
        self.listAPs = listAPs  # A list of application identifiers (APs).
        self.listORAPs = listORAPs  # A list of original application identifiers (ORAPs).
        self.df = df  # A pandas DataFrame containing filtered publication numbers.
        # An instance of OPSClient, initialized with API credentials.
        self.client: OPSClient = OPSClient(key=os.getenv("OPS_KEY"), secret=os.getenv("OPS_SECRET"))        
        self.familyRoot = familyRoot  # Represents the root of the patent family.        
        self.workdir = "/home/jovyan/output" # The directory where files will be stored.        
        os.makedirs(self.workdir, exist_ok=True)
        self.application_tree_file_path = os.path.join(self.workdir, f"{self.tree.recInp}_first_output.txt")
        self.priority_tree_file_path = os.path.join(self.workdir, f"{self.tree.recInp}_second_output.txt")        

    from collections import Counter

    def process_tree(self, mode):
        """
        Processes a tree structure for either application or priority trees, generating a summary text file.

        Args:
            mode (str): Determines the tree type, either "application" or "priority".

        Returns:
            dict: The last processed root node.
        """
        try:
            # print("process_tree: self.listORAPs:", self.listORAPs )
            if self.listORAPs is None:
                print("Error: listORAPs is None")
                return

            if not self.listAPs:
                print("Error: listAPs is None or empty")
                return

            listApCCs = ['WO' if len(word) > 2 and word[2] == 'W' else word[:2] for word in self.listAPs]
            country_code_counts = Counter(listApCCs)  # Count occurrences of each country code

            # creates a formatted comment for divisional applications, including the number of applications per country code.
            applicationComment = 'including: ' + ' + '.join(
                f'{count} {code}{"s" if count > 1 else ""}' for code, count in country_code_counts.items()
            )
            tree_comment = f'Divisional Applications ({self.df.shape[0]}) {applicationComment}'

            if not self.application_tree_file_path or not self.priority_tree_file_path:
                raise ValueError("Error: Tree file paths are None or invalid.")

            processed_nodes = set()
            written_aps = set()
            
            file_path = self.application_tree_file_path if mode == "application" else self.priority_tree_file_path
            
            # The method writes this information to a tree file for later inspection.
            node_key = 'root_ap' if mode == "application" else 'root_pr'
            # date_key = 'root_ap_date' if mode == "application" else 'root_pr_date'
            
            start_message = "Starting Extended Family Divitree Generation with" if mode == "application" else "Starting Simple Family DiviTree Generation"
        
            with open(file_path, 'w') as tree_file:
                tree_file.write(f'\n{start_message} {self.tree.recInp}\n')
                tree_file.write(f'{tree_comment}\n\n') #  ({"default" if mode == "application" else "alternative"} tree)\n\n')

                # # Filter only dict-type entries and sort them
                # valid_roots = {
                #     k: v for k, v in self.root.items() if isinstance(v, dict)
                # }

                # def parse_date_safe(date_str):
                #     try:
                #         return datetime.strptime(date_str, "%Y-%m-%d")
                #     except:
                #         return datetime.max  # push invalid/missing dates to the end
                        
                # # 🧠 SORT ROOT NODES BY DATE BEFORE PROCESSING
                # valid_root_items = sorted(
                #     ((k, v) for k, v in self.root.items() if isinstance(v, dict)),
                #     key=lambda item: item[1].get('root_ap_date' if mode == "application" else 'root_pr_date', ''),
                #     reverse=False  # because your original code loops from high to low
                # )
                
                # current_root = None  # Ensure it's always defined
                # for _, current_root in valid_root_items:
                # print("self.root:", self.root)
                for r in range(len(self.root) + 1, 0, -1):
                    current_root = self.root.get(r, {})
                    # print("current_root:", current_root)
                    if not isinstance(current_root, dict):
                        print(f"Warning: Expected dict for root, got {type(current_root)}")
                        continue

                    my_node = current_root.get(node_key, [])
                    root_an = current_root.get('root_an', '')  
                    root_ap = current_root.get('root_ap', '')                    
                    root_orap = current_root.get('root_orap', '')
                    # print(f"Processing node {my_node}, root_an {root_an}, root_ap {root_ap}, root_orap {root_orap}")
                    # if root_orap in self.listORAPs:
                    #     words = self.listORAPs
                    #     words.remove(root_orap)
                    #     self.listORAPs = " ".join(words)
                        
                    # root_evnt = current_root.get('root_evnt', '')  
                    
                    if mode == "priority" and not isinstance(my_node, list):
                        my_node = [my_node] if my_node else []
                        
                    # print("my_node in process_tree method:", my_node)
                
                    for node in (my_node if isinstance(my_node, list) else [my_node]):
                        # print(f"DEBUG: Processing priority mode - node {node}, root_ap {root_ap}, root_orap {root_orap}")
                        if isinstance(node, str) and node not in processed_nodes:
                            self.process_root(current_root, tree_file, processed_nodes, mode, written_aps)
                            # print(f"Generating tree for: {node} at level 1")
                            
                            if mode == "application":                                
                                self.generate_tree(node, 1, tree_file, processed_nodes, current_root, mode)
                            elif mode == "priority":
                                # Process each node (which could be a priority)
                                for node2 in (my_node if isinstance(my_node, list) else [my_node]):
                                    if isinstance(node2, str) and node2 not in processed_nodes:
                                        self.generate_tree(node2, 1, tree_file, processed_nodes, current_root, mode)
                                # Ensure the root application itself is visited
                                for candidate in [root_ap, root_orap]:
                                    if candidate and candidate not in processed_nodes:
                                        self.generate_tree(candidate, 1, tree_file, processed_nodes, current_root, mode)
                        # else:
                        #     print(f"Skipping node {node} (already processed or invalid)")
    
            print(f'Tree processing completed.\n')
        except Exception as e:
            print(f"Error during process_tree ({mode}): {e}")

        return current_root
        
    def process_root(self, current_root, tree_file, processed_files, mode, written_aps):
        """
        This method processes the current root node of the tree and writes its information into the tree file:
        it identifies key attributes like root_an (application number) and root_ap (application ID).
        Depending on the initFlag, it invokes specialized methods (process_priorities(), process_applications(), etc.) to process different aspects of the node.
        The method checks the last 6 characters of the application to see if it matches the recInp value and formats it accordingly.
        Process a single root node, extracting relevant information and writing it to the tree file.
        Also invokes specific methods depending on the value of the 'initFlag' to further process
        entities like priorities, applications, and legal events.

        Args:
            current_root (dict): Current root node containing application and patent data.
            tree_file (file): The file object to which the processed tree information is written.
        """
        
        root_an = current_root.get('root_an', '').strip()
        root_ap = current_root.get('root_ap', '').strip()
        root_pr = current_root.get('root_pr', '')     
        rec_inp_right_8 = self.tree.recInp[-8:]  # Get the last 8 characters of recInp
        # print("root_an, root_ap, root_pr, rec_inp_right_8:", root_an, root_ap, root_pr, rec_inp_right_8)
            
        # The method processes root attributes and writes them to the tree file in a hierarchical format.
        
        if root_ap and root_ap not in processed_files and root_ap not in written_aps:
            if root_ap.endswith(rec_inp_right_8):
                # print("a. {root_ap}:", {root_ap})
                tree_file.write(f', {root_ap}* \n')
            elif 'EP' not in root_an and root_an.endswith(rec_inp_right_8):
                if root_an and root_an != root_ap:
                    # print("b. {root_an}, {root_ap}:", {root_an}, {root_ap})
                    # tree_file.write(f', {root_ap} \n') # Write with a leading comma
                    tree_file.write(f', {root_an}* / {root_ap} \n') # Write with a leading comma                
                else:
                    # print("c. {root_ap}:", {root_ap})
                    tree_file.write(f', {root_ap}* \n') # Write with a leading comma
            else:
                if root_an and root_an != root_ap:
                    # print("d. {root_an}, {root_ap}:", {root_an}, {root_ap})
                    if root_an.endswith(rec_inp_right_8):
                        tree_file.write(f', {root_an}* / {root_ap} \n') # Write with a leading comma
                    else:
                        tree_file.write(f', {root_an} / {root_ap} \n') # Write with a leading comma                        
                    # tree_file.write(f', {root_ap} \n') # Write with a leading comma                    
                else:
                    # print("e. {root_ap}:", {root_ap})                    
                    tree_file.write(f', {root_ap} \n') # Write with a leading comma

            if mode == "priority":
                # Add root_ap to the set of written application IDs
                written_aps.add(root_ap)
    
            # Mapping initFlag values to corresponding methods
            process_methods = {
                'Show_priorities': self.process_priorities,
                'Show_applications': self.process_applications,
                'Show_parents': self.process_parents,
                'Show_publications': self.process_publications,
                'Show_citations': self.process_citations,
                'Show_classifications': self.process_classifications,
                'Show_parties': self.process_parties,                
                'Show_legal_events': self.process_legal_events,
                'Show_images': self.process_images
            }

            # The initFlag is used to control the type of information processed (e.g., citations, classifications, parties).            
            if self.initFlag in process_methods:
                # print("self.initFlag in process_root:", self.initFlag)
                process_methods[self.initFlag](current_root, 1, tree_file)
        
    def generate_tree(self, my_node, level, tree_file, processed_nodes, current_root, mode="application"):
        """
        Recursively generate a tree structure by navigating through nodes and writing them to the tree file.
        This method tracks processed nodes and ensures no duplicates are included.

        Args:
            my_node (str): Identifier of the current node.
            level (int): Depth level for indentation.
            tree_file (file): File object for writing tree structure.
            processed_nodes (set): Set of already processed application nodes.
            current_root (dict): Root node details (e.g., 'root_an' and 'root_ap').
            mode (str): Type of tree ("application" or "priority").
        """
        # Check if the current node has already been processed, avoid reprocessing.
        # print("my_node, processed_nodes:", my_node, processed_nodes)
        if my_node in processed_nodes:
            return  

        # Mark the current node as processed.
        processed_nodes.add(my_node)

        # Increment the level for indentation.
        level += 1

        # Dictionary to track sibling nodes.
        sibling = {'0': 0}
        # print("my_node:", my_node)
        
        # Variable to track the previous my_node
        # prev_my_node = None

        # Iterate through tree data in reverse order.
        for t in range(int(self.tree.orapNb) - 1, -1, -1):
            orap_list = set(self.tree.orap[t].split(',')) if isinstance(self.tree.orap[t], str) else set()

            if my_node in orap_list and self.tree.orap[t] != '': # if my_node in self.tree.orap[t] and self.tree.orap[t] != '': # and my_node in self.listORAPs:

                # # Check if previous my_node also appears in the same orap list (if available)
                # if prev_my_node and prev_my_node not in orap_list:
                #     print(f"Warning: {prev_my_node} is missing in orap[{t}] ({orap_list}), but it should be linked to the same child.")
 
                # print(f"t: {t} tree.orap[t] {self.tree.orap[t]}, my_node: {my_node}")  
                # print(f"t: {t} self.tree.evnt[t]: {self.tree.evnt[t]}")
                # # Check the type and value of self.tree.pr[t]
                # print(f"Type of self.tree.pr[{t}]:", type(self.tree.pr[t]))
                # print(f"Value of self.tree.pr[{t}]:", self.tree.pr[t])

                # if self.tree.pr[t] != []:
                #     print("self.tree.ap[t]:", self.tree.ap[t])
                #     print("self.tree.an[t]:", self.tree.an[t])
                #     print("self.tree.pr[t]:", self.tree.pr[t])
                s = sibling['0'] + 1
                sibling[s] = {
                    'an': self.tree.an[t].split()[0] if isinstance(self.tree.an[t], str) else '',
                    'ap': self.tree.ap[t].split()[0] if isinstance(self.tree.ap[t], str) else '',
                    'pn': self.tree.pn[t].split()[0] if isinstance(self.tree.pn[t], str) else '',
                    'pr': list(self.tree.pr[t]) if hasattr(self.tree, 'pr') and isinstance(self.tree.pr[t], (list, tuple)) else '',
                    'orap': self.tree.orap[t],
                    's': self.tree.ap[t].split()[0] if isinstance(self.tree.ap[t], str) else '',
                    'evnt': self.tree.evnt[t] if hasattr(self.tree, 'evnt') and isinstance(self.tree.evnt[t], list) else []
                }
                # print("sibling[s]:", sibling[s])
                # print("t:", t)
                # print(f"Found child: {sibling[s]['ap']}")
                # print(f"Found publication: {sibling[s]['pn']}")
                # print(f"Found prio: {sibling[s]['pr']}")
                # print(f"Found parent: {sibling[s]['orap']}")
                # print(f"Found evnt: {sibling[s]['evnt']}")
                # print()
                # Update prev_my_node for next iteration
                # prev_my_node = sibling[s]['s'] # my_node
                # Recursively process children if not already processed
                
                sibling['0'] = s                
        # print()
        
        # If siblings exist, process them.
        if sibling['0'] > 0:
            rec_inp_right_8 = str(self.tree.recInp)[-8:]
            root_an = current_root.get('root_an', '')
            root_ap = current_root.get('root_ap', '')
            # print("root_an, root_ap, current_root:", root_an, root_ap, current_root)

            # Sort siblings by earliest priority date
            def get_priority_date(sibling_entry):
                prios = sibling_entry.get('pr', [])
                try:
                    return min(datetime.strptime(prio[:10], '%Y-%m-%d') for prio in prios if isinstance(prio, str) and len(prio) >= 10)
                except:
                    return datetime.max

            # def build_priority_graph(applications):
            #     """Build a mapping of application -> [list of apps that claim it as priority]."""
            #     priority_graph = {}
            #     app_by_id = {app['s']: app for app in applications}

            #     for app in applications:
            #         prios = app.get('pr', [])
            #         for prio in prios:
            #             if prio not in priority_graph:
            #                 priority_graph[prio] = []
            #             priority_graph[prio].append(app['s'])
            #     return priority_graph, app_by_id

            # def traverse_priority_tree(root_id, priority_graph, app_by_id, visited, level=0, tree_file=None):
            #     if root_id in visited:
            #         return
            #     visited.add(root_id)

            #     app = app_by_id.get(root_id)
            #     if not app:
            #         return

            #     label = f"{root_id}"
            #     if tree_file:
            #         tree_file.write(', ' * level + label + "\n")

            #     for child_id in sorted(priority_graph.get(root_id, []), key=lambda x: get_priority_date(app_by_id.get(x, {}))):
            #         traverse_priority_tree(child_id, priority_graph, app_by_id, visited, level+1, tree_file)

            # priority_graph, app_by_id = build_priority_graph(sibling_list)
            # visited = set()
            # with open('tree_output.txt', 'w') as tree_file:
            #     for app_id in sorted(app_by_id, key=lambda x: get_priority_date(app_by_id[x])):
            #         if app_id not in visited:
            #             traverse_priority_tree(app_id, priority_graph, app_by_id, visited, 0, tree_file)

            
            # Extract and sort siblings
            unsorted_siblings = [sibling[s] for s in range(1, sibling['0'] + 1)]
            sorted_siblings = sorted(unsorted_siblings, key=get_priority_date)

            # Rebuild the sibling dictionary with sorted entries
            for idx, entry in enumerate(sorted_siblings, 1):
                sibling[idx] = entry
                
            # Process each sorted sibling
            for s in range(1, sibling['0'] + 1):
                s_ap = sibling[s]['s']
                s_an = sibling[s]['an']
                # print("s_ap:", s_ap)
                # print("s_an:", s_an)
                if isinstance(s_ap, str) and s_ap not in [root_an, root_ap] and s_ap not in processed_nodes: 
                    tree_label = '' # tree_label = "(default tree)" if mode == "application" else "(alternative tree)"                    
                    # Write sibling data to the file with appropriate indentation.
                    if s_ap.find(rec_inp_right_8) >= 0:
                        tree_file.write(', ' * level + f"{s_ap}* {tree_label}\n")
                    elif 'EP' not in s_ap and s_an.find(rec_inp_right_8) >= 0:
                        tree_file.write(', ' * level + f"{s_an}* {tree_label}\n")
                    else:
                        tree_file.write(', ' * level + f"{s_ap} {tree_label}\n")

                    # Mapping initFlag values to corresponding methods.
                    process_methods = {
                        'Show_publications': self.process_publications,
                        'Show_citations': self.process_citations,
                        'Show_classifications': self.process_classifications,
                        'Show_parties': self.process_parties,
                        'Show_images': self.process_images
                    }

                    # Call specific methods based on the initFlag.
                    if self.initFlag == 'Show_priorities':
                        self.process_priorities(sibling[s]['pr'], level, tree_file)
                    elif self.initFlag == 'Show_applications':
                        self.process_applications(sibling[s]['ap'], level, tree_file)
                    elif self.initFlag == 'Show_parents':
                        self.process_parents(sibling[s]['orap'], level, tree_file)
                    elif self.initFlag == 'Show_legal_events' and sibling[s]['evnt'] and sibling[s]['evnt'] != []:
                        # self.process_legal_events('', level, tree_file)
                        self.process_legal_events({'legal_events': sibling[s]['evnt']}, level, tree_file)
                    elif self.initFlag in process_methods:
                        sibling_dict = {'root_pn': sibling[s]['pn']}
                        process_methods[self.initFlag](sibling_dict, level, tree_file)

                    # Recursive call for child nodes.
                    child_node = sibling[s]['ap'].strip()
                        
                    # print()
                    # print("child_node:", child_node)
                    # print("processed_nodes:", processed_nodes)
                    # It recursively processes children nodes until all nodes are processed.                    
                    if child_node and child_node not in processed_nodes:
                        # print(f"Generating tree for: {child_node} and at level {level}")
                        # print(f"Recursing into: {child_node}, Level: {level}, Processed: {processed_nodes}")
                        # Recursively call generate_tree for the child node.
                        self.generate_tree(child_node, level, tree_file, processed_nodes, current_root, mode)

            level -= 1
        return level, sibling
        
    def process_generic(self, current_root, level, tree_file, key, formatter=None):
        """
        Process and write data from the current root node to the tree file.

        Args:
            current_root (dict): Current root node data containing various attributes.
            level (int): The current depth in the tree structure, used for indentation in the output file.
            tree_file (file object): File object where the processed data will be written.
            key (str): The key in current_root that holds the data to process (e.g., 'root_ap', 'root_an').
            formatter (function, optional): A function to format the output data before writing.
               The formatter should handle individual items (e.g., strings or dictionaries) as
               the method applies it to each element in lists or nested structures.
        """
        def write_data(data, level, myKey, formatter=None):
            """
            Helper function to recursively write data to the tree file.
            It handles different data types (str, list, dict) and applies formatting if a formatter is provided.

            Args:
                data: The data to write, which can be a string, list, or dictionary.
                level: The current level of recursion used to control the depth (indentation) of the output.
                formatter: A function used to format the data before writing. If not provided, raw data is written.                
            """      
            # Handle string data
            if isinstance(data, str):
                indent = ". " * level
                tree_file.write(f'{indent}{formatter(data) if formatter else data}\n')
            # Handle list data (process each item recursively)
            elif isinstance(data, list):
                for index, item in enumerate(data):
                    # print("formatter:", formatter)
                    # print("myKey:", myKey)
                    if myKey == 'root_pr':
                        # tree_file.write(f'{indent}- Prio {index + 1}:\n')
                        write_data(item, level + 1, formatter)
                    elif myKey == 'root_evnt':
                        # tree_file.write(f'{indent}- Event {index + 1}:\n')
                        write_data(item, level + 1, formatter)
                    else:
                        # print("item:", item)                        
                        # tree_file.write(f'{indent}- Item {index + 1}:\n')
                        write_data(item, level + 1, formatter)
            # Handle dictionary data (formatting option provided)
            elif isinstance(data, dict):
                myDescFlag = False
                for key, value in data.items():
                    if key in {'code', 'desc'}:
                        # print("key:", key)
                        # print("value:", value)
                        if key == 'code' and value == 'DFPE':
                            myDescFlag = True
                        elif myDescFlag:
                            write_data(f'{key}:{value}', level + 1, formatter)     
                    elif key not in {'nested_data', 'dateMigr', 'infl', 'texts'}:
                        # print("key:", key)
                        # print("value:", value)
                        # tree_file.write(f'{key}:\n')
                        write_data(f'{key}:{value}', level + 1, formatter)                            
            else:
                indent = ". " * level
                tree_file.write(f'{indent}{formatter(data) if formatter else str(data)}\n')    
            return

# def write_data(data, level, myKey, formatter=None):
#     """
#     Helper function to recursively write data to the tree file.
#     It handles different data types (str, list, dict) and applies formatting if a formatter is provided.

#     Args:
#         data: The data to write, which can be a string, list, or dictionary.
#         level: The current level of recursion used to control the depth (indentation) of the output.
#         myKey: A key indicating the type of data being processed (e.g., 'root_evnt').
#         formatter: A function used to format the data before writing. If not provided, raw data is written.
#     """
    
#     # Handle string data
#     if isinstance(data, str):
#         indent = ". " * level
#         tree_file.write(f'{indent}{formatter(data) if formatter else data}\n')

#     # Handle list data (process each item recursively)
#     elif isinstance(data, list):
#         for index, item in enumerate(data):
#             if myKey == 'root_pr':
#                 write_data(item, level + 1, myKey, formatter)
#             elif myKey == 'root_evnt':
#                 if formatter:
#                     formatted_event = formatter({'legal_events': [item]})  # Apply formatter to a single event
#                     write_data(formatted_event, level, myKey, formatter)
#                 else:
#                     write_data(item, level + 1, myKey, formatter)
#             else:
#                 write_data(item, level + 1, myKey, formatter)

#     # Handle dictionary data (formatting option provided)
#     elif isinstance(data, dict):
#         if myKey == 'root_evnt':
#             if formatter:
#                 formatted_event = formatter({'legal_events': [data]})  # Apply formatter to a single event
#                 write_data(formatted_event, level, myKey, formatter)
#             else:
#                 write_data(data, level + 1, myKey, formatter)
#         else:
#             for key, value in data.items():
#                 if key not in {'nested_data', 'dateMigr', 'infl', 'texts'}:
#                     write_data(f'{key}: {value}', level + 1, myKey, formatter)

#     # Handle other types of data
#     else:
#         indent = ". " * level
#         tree_file.write(f'{indent}{formatter(data) if formatter else str(data)}\n')

#     return

        
        # Main logic to extract the relevant data from current_root and process it
        if isinstance(current_root, dict): # instead of dict only
            # Retrieve the data corresponding to the provided key from current_root
            data = current_root.get(key, None)
            if data is not None:
                write_data(data, level, key, formatter)
            else:
                write_data(current_root, level, key, formatter)
                
        # If current_root is already a string or list, process it directly
        elif isinstance(current_root, (str, list)):
            write_data(current_root, level, key, formatter)

        # Handle unexpected data types
        else:
            logging.warning(f"Unexpected current_root format: {type(current_root)}")
        
    def process_priorities(self, current_root, level, tree_file):
        """
        Process and write priority data from the current root node to the tree file.

        Args:
            current_root (dict): Current root node data, containing information about priorities.
            level (int): The current depth in the tree structure, used for indentation in the output file.
            tree_file (file object): The file object for writing tree structure or priority information.
        """
        # Use the process_generic method to handle priority data processing.
        # It passes 'root_pr' as the key, which contains the priority data in the current_root node.
        self.process_generic(current_root, level, tree_file, key='root_pr')

    def process_applications(self, current_root, level, tree_file):
        """
        Process and write application data from the current root node to the tree file.

        Args:
            current_root (str or dict): Current root node data or application identifier.
            level (int): The current depth in the tree structure, used for indentation in the output file.
            tree_file (file object): The file object for writing tree structure or application information.
        """
        # Use the process_generic method to handle application data processing.
        # It passes 'root_ap' as the key, which contains the application data in the current_root node.      
        self.process_generic(current_root, level, tree_file, key='root_ap')

    def process_parents(self, current_root, level, tree_file):
        """
        Process and write parent data from the current root node to the tree file.

        Args:
            current_root (str or dict): Current root node data or parent identifier.
            level (int): The current depth in the tree structure, used for indentation in the output file.
            tree_file (file object): The file object for writing tree structure or parent information.
        """        
        # Use the process_generic method to handle parent data processing.
        # It passes 'root_orap' as the key, which contains the parent data in the current_root node.     
        self.process_generic(current_root, level, tree_file, key='root_orap')

    def process_publications(self, current_root, level, tree_file):
        """
        Process and write publication data from the current root node to the tree file.

        Args:
            current_root (str or dict): Current root node data or publication identifier.
            level (int): The current depth in the tree structure, used for indentation in the output file.
            tree_file (file object): The file object for writing publication information.
        """        
        # Use the process_generic method to handle publication data processing.
        # It passes 'root_pn' as the key, which contains the publication data in the current_root node.        
        self.process_generic(current_root, level, tree_file, key='root_pn')

    def format_legal_events(self, event_data):
        """
        Format legal event data into a readable string.

        Args:
            event_data (dict or any): Data containing legal event information.

        Returns:
            str: A formatted string representing the legal event data, or a default message if no data is available.
        """
        # If event_data is empty or None, return a default message  
        if not event_data or (isinstance(event_data, dict) and 'legal_events' in event_data and not event_data['legal_events']): 
            # return None  # Skip adding this field if it's empty
            event_data = 'No legal events available.'
            return event_data

        # If event_data is a dictionary, format each legal event in the list
        if isinstance(event_data, dict) and 'legal_events' in event_data:
            formatted_events = []
            for event in event_data['legal_events']:
                event_type = event.get('legal_event_code', 'Unknown Event')
                event_date = event.get('legal_event_date_migr', 'Unknown Date')
                event_desc = event.get('legal_event_desc', 'No Description')
                event_infl = event.get('legal_event_infl', 'No Influence')

                # Construct the formatted string for each event
                formatted_events.append(f"{event_type}: {event_desc}")
                # formatted_events.append(f"{event_type} on {event_date}: {event_desc} ({event_infl}) [{event_texts}]")
            return '\n'.join(formatted_events)
        
        # For other types of data, convert them to a string representation
        return str(event_data)

# def format_legal_events(self, event_data, level=0, tree_file=None):
#     """
#     Format legal event data into a readable string and optionally write to a tree file.

#     Args:
#         event_data (dict or any): Data containing legal event information.
#         level (int): Indentation level for tree file formatting.
#         tree_file (file object, optional): File object where formatted data should be written.

#     Returns:
#         str: A formatted string representing the legal event data, or a default message if no data is available.
#     """
#     # Return default message if no legal event data is available
#     if not event_data or (isinstance(event_data, dict) and 'legal_events' in event_data and not event_data['legal_events']):
#         return 'No legal events available.'

#     formatted_events = []

#     # Process legal event data if it is a dictionary containing 'legal_events'
#     if isinstance(event_data, dict) and 'legal_events' in event_data:
#         for event in event_data['legal_events']:
#             event_code = event.get('legal_event_code', 'Unknown Event')
#             event_date = event.get('legal_event_date_migr', 'Unknown Date')
#             event_desc = event.get('legal_event_desc', 'No Description')
#             event_infl = event.get('legal_event_infl', 'No Influence')
#             event_texts = event.get('texts', '').split('|')  # Split multiple texts if needed

#             dfpe_flag = False
#             event_details = []

#             # Extract relevant fields
#             for key, value in event.items():
#                 if key == 'code' and value == 'DFPE':
#                     dfpe_flag = True  # Flag that DFPE event was encountered
#                 elif key == 'desc' and dfpe_flag:
#                     event_details.append(f"{key}: {value}")
#                 elif key not in {'nested_data', 'dateMigr', 'infl', 'texts'}:
#                     event_details.append(f"{key}: {value}")

#             # Construct formatted event string
#             formatted_event_str = f"- {event_code}: {event_desc} ({event_date})"
#             if event_details:
#                 formatted_event_str += "\n  " + "\n  ".join(event_details)

#             formatted_events.append(formatted_event_str)

#             # Write to tree file if provided
#             if tree_file:
#                 tree_file.write(', ' * (level + 2) + formatted_event_str + "\n")
#                 for text in event_texts:
#                     tree_file.write(', ' * (level + 3) + f"{text.strip()}\n")

#     return '\n'.join(formatted_events) if formatted_events else 'No legal events available.'
    
                    # for event in sibling[s]['evnt']:
                    #     event_code = event.get('code', 'N/A')
                    #     event_desc = event.get('desc', 'No Description')
                    #     event_date = event.get('dateMigr', 'Unknown Date')
                    #     event_texts = event.get('texts', '').split('|')  # Split multiple texts if needed

                    #    # Write formatted event information
                    #    tree_file.write(', ' * (level + 2) + f"- {event_code}: {event_desc} ({event_date})\n")
        
                    #    # Write additional text information if available
                    #    for text in event_texts:
                    #        tree_file.write(', ' * (level + 3) + f"{text.strip()}\n")
    
    def process_legal_events(self, current_root, level, tree_file):
        """
        Process and write legal event data from the current root node to the tree file.

        Args:
            current_root (str or dict): Current root node data or application identifier.
            level (int): The current depth in the tree structure for indentation.
            tree_file (file object): File object for the tree file where data will be written.
        """
        # Calls the generic processing method with a formatter specific to legal events
        self.process_generic(current_root, level, tree_file, key='root_evnt', formatter=self.format_legal_events)
                
    def retrieve_biblio_data(self, current_root, level, tree_file, data_type, extraction_func=None, output_format_func=None):
        """
        A unified method to process different types of data (e.g., citations, classifications, parties, images) 
        from the current root node and write it to a tree file.

        Args:
            - current_root (dict): The document number or dictionary containing document number information.
            - level (int): The level in the tree for formatting output.
            - tree_file (File): The file object to write the processed data.
            - data_type (str): The type of data to process ('citations', 'classifications', 'parties', 'images').
            - extraction_func (callable): A function to extract specific data from the retrieved bibliographic information.
            - output_format_func (callable): A function to format the extracted data before writing to the file.
        """
        
        # Check if the current_root is valid and contains the expected key 'root_pn'
        if not isinstance(current_root, dict) or 'root_pn' not in current_root:
            print(f"Invalid 'current_root': {current_root}")
            return

        # Extract the publication number from the current_root
        pub_number = current_root.get('root_pn', '')

        # Initialize biblio_data to handle the case where retrieval fails
        biblio_data = None  # Initialize biblio_data to handle the case where retrieval fails
        try:
            # Determine the endpoint and output type based on the data_type
            endpoint = "biblio"
            output_type = "Dataframe"
            if data_type == 'images':
                endpoint = "images"
                output_type = "Raw"
            
            # Retrieve the bibliographic, image, or legal data for the document
            biblio_data = self.client.published_data(
                reference_type="publication",
                input=models.Docdb(pub_number[2:-2], pub_number[:2], pub_number[-2:], date=None),
                endpoint=endpoint,
                constituents=[],
                output_type=output_type,
            )
        except requests.exceptions.RequestException as e:  # Catch any request exception
            print(f"HTTP error occurred: {e}")
            if hasattr(e, 'response'):  # Check if the exception has a response attribute (likely in newer versions)
                if e.response.status_code == 404:
                    print(f"Publication number {pub_number} not found. Skipping.")
                else:
                    raise  # Re-raise other errors
            else:  # For older versions, assume it's a 404 based on the message
                print(f"Publication number {pub_number} not found. Skipping.")

        # display(biblio_data)
        
        # If biblio_data is not retrieved, skip the rest of the process
        if biblio_data is None:
            return
        
        # Extract and process the relevant data        
        extracted_data = extraction_func(biblio_data) if extraction_func else None
        # print("extracted_data:", extracted_data)
        
        # Format the output and write to file if data exists
        if extracted_data:
            formatted_output = output_format_func(extracted_data) if output_format_func else str(extracted_data)
            # print("formatted_output:", formatted_output)
            if tree_file:
                tree_file.write(f'{". " * (level + 1)}{formatted_output}\n')

    def extract_citations(self, biblio_df):
        """
        Extracts citation information from a bibliographic DataFrame.

        Args:
            biblio_df (pandas.DataFrame): DataFrame containing bibliographic data.

        Returns:
            list: A list of citations extracted from the DataFrame.
        """
        citations_list = []
        
        # Check if the DataFrame contains the expected column
        if 'bibliographic-data|references-cited' in biblio_df.columns:
            # Iterate over each entry in the 'bibliographic-data|references-cited' column
            for citations_data in biblio_df['bibliographic-data|references-cited']:
                # Check if the entry is a dictionary and contains 'citation'
                if isinstance(citations_data, dict) and 'citation' in citations_data:
                    citations = citations_data['citation']
                    # If 'citation' is a list, extend citations_list with its elements
                    if isinstance(citations, list):
                        citations_list.extend(citations)                        
                    # If 'citation' is a dictionary, append it to citations_list
                    elif isinstance(citations, dict):
                        citations_list.append(citations)
        return citations_list

    def format_citations(self, citations_list):
        """
        Format a list of citations into a readable string.

        Args:
            citations_list (list): List of citations to format, each citation is expected to be a dictionary.

        Returns:
            str: A formatted string representation of the citations.
        """
        # Convert the list of citation dictionaries into a DataFrame for easier manipulation
        citations_df = pd.json_normalize(citations_list)
        
        # Check for the presence of key 'patcit.@dnum-type' and filter citations based on this column
        if 'patcit.@dnum-type' in citations_df.columns:
            citation_filter = (citations_df['patcit.@dnum-type'] == 'publication number')
        else:
            citation_filter = pd.Series([False] * len(citations_df))

        # Add additional filter for non-null values in 'nplcit.@num' if it exists
        if 'nplcit.@num' in citations_df.columns:
            citation_filter |= citations_df['nplcit.@num'].notna()

        # Apply the filters and drop duplicate citations based on specific columns
        citations_df = citations_df[citation_filter].drop_duplicates(subset=['@sequence', 'patcit.@num'], keep='first')
    
        # Define a helper function to extract the document number from the 'patcit.document-id'
        def extract_doc_number(doc_ids):
            if isinstance(doc_ids, list):
                epodoc_doc_number = None
                docdb_doc_number = None
                for doc in doc_ids:
                    if doc.get('@document-id-type') == 'epodoc':
                        epodoc_doc_number = doc.get('doc-number')
                    elif doc.get('@document-id-type') == 'docdb':
                        docdb_doc_number = doc.get('doc-number')
                return epodoc_doc_number or docdb_doc_number
            elif isinstance(doc_ids, dict):
                # Handle the case where doc_ids is a single dictionary (unlikely, but just in case)
                if doc_ids.get('@document-id-type') == 'epodoc':
                    return doc_ids.get('doc-number')
                elif doc_ids.get('@document-id-type') == 'docdb':
                    return doc_ids.get('doc-number')
            return None

        # Define a helper function to extract 'XP' number from 'nplcit.text'
        def extract_xp_number(npl_text):
            if isinstance(npl_text, str) and 'XP' in npl_text:
                return 'XP' + npl_text.split('XP')[-1].split()[0]
            return None
    
        # Extract document numbers and 'XP' numbers if corresponding columns are present
        if 'patcit.document-id' in citations_df.columns:
            citations_df['extracted_doc_number'] = citations_df['patcit.document-id'].apply(lambda x: extract_doc_number(x))
        else:
            citations_df['extracted_doc_number'] = None

        if 'nplcit.text' in citations_df.columns:
            citations_df['extracted_xp_number'] = citations_df['nplcit.text'].apply(lambda x: extract_xp_number(x))
        else:
            citations_df['extracted_xp_number'] = None

        # Combine extracted document numbers and 'XP' numbers into a single column
        citations_df['formatted_citation'] = citations_df['extracted_doc_number'].combine_first(citations_df['extracted_xp_number'])

        # Collect unique cited phases and append it to the formatted citation if present
        cited_phase = citations_df['@cited-phase'].dropna().unique()
        cited_phase_comment = f" (cited-phase: {cited_phase[0]})" if len(cited_phase) == 1 else ""
        
        return f"{str(citations_df['formatted_citation'].dropna().tolist())}{cited_phase_comment}"

    def process_citations(self, current_root, level=None, tree_file=None):
        """
        Process and write citation data from the current root node to the tree file.

        Args:
            current_root (dict): The document number or dictionary containing document number information.
            level (int, optional): The level in the tree for formatting output. Defaults to None.
            tree_file (file object, optional): File object for writing the processed data. Defaults to None.
        """
        # Call the retrieve_biblio_data method with specific parameters for processing citations
        self.retrieve_biblio_data(
            current_root=current_root,  # Document number or dictionary with document number information
            level=level,                # Level for formatting output
            tree_file=tree_file,        # File object to write the formatted data
            data_type='citations',      # Type of data to process
            extraction_func=self.extract_citations,  # Function to extract citation data from the retrieved bibliographic information
            output_format_func=self.format_citations  # Function to format the extracted citation data before writing to the file
        )

    def extract_classifications(self, biblio_df):
        """
        Extracts and processes patent classification data from a DataFrame containing bibliographic information.

        Args:
            biblio_df (pd.DataFrame): DataFrame containing bibliographic data, including patent classifications.

        Returns:
            list: A list of unique patent classification strings.
        """
        classification_data = []

         # Check if 'bibliographic-data|patent-classifications' column exists in the DataFrame
        if 'bibliographic-data|patent-classifications' in biblio_df.columns:
            # Iterate through each row of the DataFrame
            for index, row in biblio_df.iterrows():
                classification_info = row['bibliographic-data|patent-classifications']
                # Debugging output
                # print(f"Processing classifications for row {index}: {classification_info}")

                # Ensure the classification information is a dictionary and contains 'patent-classification'
                if isinstance(classification_info, dict) and 'patent-classification' in classification_info:
                    classifications = classification_info['patent-classification']

                    # If classifications are in list format, process each classification
                    if isinstance(classifications, list):
                        for classification in classifications:
                            section = classification.get('section', 'Unknown')
                            _class = classification.get('class', 'Unknown')
                            subclass = classification.get('subclass', 'Unknown')
                            main_group = classification.get('main-group', 'Unknown')
                            subgroup = classification.get('subgroup', 'Unknown')

                            # Create a CPC (Cooperative Patent Classification) item string
                            cpc_item = f"{section}{_class}{subclass}{main_group}/{subgroup}"
                            # Debugging output
                            # print("Extracted CPC item:", cpc_item)

                            # Append unique CPC items to the classification_data list
                            if cpc_item not in classification_data:
                                classification_data.append(cpc_item)
                    else:
                        print("No classifications found in this entry.")
                else:
                    print(f"No patent classifications found in row {index}.")

        return classification_data
    
    def format_classifications(self, classification_data):
        """
        Formats the list of patent classification strings into a single string representation.

        Args:
            classification_data (list): A list of patent classification strings.

        Returns:
            str: A string representation of the classification data.
        """
        # Debugging output
        # print(f"Formatting classification data: {classification_data}")
        
        # Convert the list of classifications to a string
        return str(classification_data)

    def process_classifications(self, current_root, level=None, tree_file=None):
        """
        Process and write classification data from the current root node to the tree file.

        Args:
            current_root (dict): The document number or dictionary containing document number information.
            level (int, optional): The level in the tree for formatting output. Defaults to None.
            tree_file (file object, optional): The file object to write the processed data. Defaults to None.
        """
        # Debugging output
        # print(f"Processing classifications for {current_root}")
        
        # Retrieve and process bibliographic data
        self.retrieve_biblio_data(
            current_root,                  # The root data (document number or dictionary)
            level,                         # The indentation level for output formatting
            tree_file,                     # The file object to write the output
            'classifications',            # Type of data to retrieve (classifications)
            self.extract_classifications, # Function to extract classification data
            self.format_classifications   # Function to format the extracted classification data
        )

    def extract_party_names(self, biblio_df):
        """
        Extract names of parties (applicants, inventors, representatives) from the bibliographic DataFrame.

        Args:
            biblio_df (pd.DataFrame): DataFrame containing bibliographic data, including party information.

        Returns:
            list: A list of party names extracted from the DataFrame.
        """
        def extract_names(party_list, role):
            """
            Extract names of parties based on their role.

            Args:
                party_list (list): List of party dictionaries.
                role (str): Role of the party (e.g., 'applicant', 'inventor', 'representative').

            Returns:
                list: A list of party names.
            """            
            return [party.get(f'{role}-name', {}).get('name', '').replace('\u2002', ' ').strip(', ')
                    for party in party_list if f'{role}-name' in party]
            
        if biblio_df is None:
            return []

        # Extract relevant rows from the DataFrame
        indexes_to_iterate = list(biblio_df.head(5).index) + list(biblio_df.tail(5).index)
        indexes_to_iterate = list(set(indexes_to_iterate))  # Remove duplicates if any

        result = []
        for index in indexes_to_iterate:
            row = biblio_df.loc[index]
            parties_info = row.get('bibliographic-data|parties', {})

            if isinstance(parties_info, dict):
                applicants = parties_info.get('applicants', {}).get('applicant', [])
                inventors = parties_info.get('inventors', {}).get('inventor', [])
                representatives = parties_info.get('representatives', {}).get('representative', [])

                applicant_names = extract_names(applicants, 'applicant')
                inventor_names = extract_names(inventors, 'inventor')
                representative_names = extract_names(representatives, 'representative')

                result.extend(applicant_names)
                result.extend(inventor_names)
                result.extend(representative_names)
    
        return result

    def process_parties(self, current_root, level, tree_file):
        """
        Process and write party data (applicants, inventors, representatives) from the current root node to the tree file.

        Args:
            current_root (str or dict): Current root node data or application identifier.
            level (int): The level in the tree for formatting output.
            tree_file (file object): File object for writing the processed data.
        """
        def format_party_output(data):
            """
            Format the extracted party names into a comma-separated string.

            Args:
                data (list): List of party names.

            Returns:
                str: A comma-separated string of party names.
            """
            return ', '.join(data)

        # This method is used to retrieve the bibliographic data, extract relevant party names, and then format the extracted data for output.
        self.retrieve_biblio_data(
            current_root, 
            level, 
            tree_file, 
            'biblio', 
            extraction_func=self.extract_party_names, 
            output_format_func=format_party_output
        )
    
    def process_images(self, current_root, level, tree_file):
        """
        Process and write image data from the current root node to the tree file.

        Args:
            current_root (str or dict): Current root node data or application identifier.
            level (int): The level in the tree for formatting output.
            tree_file (file object): File object for writing the processed data.
        """
        
        def extract_image_data(image_xml):
            """
            Extracts the image path from the XML data.

            Args:
                image_xml (str): XML data containing image information.

            Returns:
                str or None: Path to the image if found, otherwise None.
            """
            root = ET.fromstring(image_xml)
            namespace = {'ops': 'http://ops.epo.org'}

            # Extract the path from the 'FirstPageClipping' document instance
            first_page_clipping = root.find('.//ops:document-instance[@desc="FirstPageClipping"]', namespace)
            if first_page_clipping is not None:
                path = first_page_clipping.get('link')
                # print(f"Extracted image path: {path}")
                return path
            # print("No FirstPageClipping found")
            return None

        def format_image_output(image_path):
            """
            Formats and saves the image, then writes a Markdown link to the image to the tree file.

            Args:
                image_path (str or None): Path to the image.

            Returns:
                str: Markdown formatted image link or a message if no image is found.
            """
            if image_path:
                # print(f"Formatting image path: {image_path}")
                fp_image_data = self.client.image(
                    path=image_path,
                    range=1,
                    document_format='application/tiff',
                )
                # print("fp_image_data:", fp_image_data)
                fp_image = Image.open(io.BytesIO(fp_image_data))
                # print("fp_image:", fp_image)
                display(fp_image)
                
                image_filename = f"image_level_{level}.tiff"
                print("image_filename:", image_filename)
                fp_image.save(image_filename)

                formatted_output = f"![Image at level {level}]({image_filename})"
                # print(f"Formatted output: {formatted_output}")
                if formatted_output:
                    tree_file.write(f"{'. ' * (level + 1)}{formatted_output}\n")          
                return formatted_output        
            return "No image found."
            
        # Initialize formatted_output to None
        formatted_output = None

        # Retrieve and format image data
        formatted_output = self.retrieve_biblio_data(
            current_root, 
            level, 
            None, 
            'images',
            extraction_func=extract_image_data,
            output_format_func=format_image_output
        )
