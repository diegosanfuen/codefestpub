import os
from pathlib import Path
import pandas as pd
import xml.etree.ElementTree as ET
import ipywidgets as widgets
from IPython.display import clear_output, display
from collections import Counter
from epo.tipdata.ops import OPSClient, models, exceptions

from patent_analysis.family_record import FamilyRecord
from patent_analysis.tree_creation import TreeCreation, TreeNode
from patent_analysis.tree_processor import TreeProcessor
from patent_analysis.install_dependencies import InstallDependencies

# Main class
class PatentProcessor:
    def __init__(self, OPSClient, models, exceptions):
        self.client = OPSClient(key=os.getenv("OPS_KEY"), secret=os.getenv("OPS_SECRET"))
        self.tree = None
        self.root = None
        self.listAPs = None
        self.listORAPs = None
        self.filtered_app_numbers = None
        self.familyRoot = None
        self.record1 = None
        self.initFlag = None
        self.is_button_clicked = False
        self.country_checkboxes = []
        
        # Initialize output widget **before** calling update_doc_number()
        self.output = widgets.Output()
        
        # Input widgets
        self.reference_type_widget = widgets.Dropdown(
            options=['application', 'publication'],
            value='application',
            description='Reference Type:'
        )
        self.doc_number_widget = widgets.Text(description='Doc Number:')
        self.country_widget = widgets.Text(description='Country:')
        self.kind_widget = widgets.Text(description='Kind:')
        self.constituents_widget = widgets.Dropdown(
            options=[None, 'biblio', 'legal'], value=None, description='Constituents:'
        )
        self.input_widget = widgets.Dropdown(
            options=[models.Docdb, models.Epodoc], value=models.Docdb, description='Input Model:'
        )
        self.output_type_widget = widgets.Dropdown(
            options=['raw', 'dataframe'], value='raw', description='Output Type:'
        )
        
        # Attach update function to reference type change
        self.reference_type_widget.observe(self.update_doc_number, names='value')
                
        self.submit_button = widgets.Button(description="Submit")        
        self.submit_button.on_click(self.on_submit_button_clicked)
    
        action_labels = [
            "Show Priorities", "Show Applications", "Show Parents", "Show Publications", "Show Citations",
            "Show Classifications", "Show Parties", "Show Legal Events", "Show Images"
        ]
        self.action_buttons = [widgets.Button(description=label) for label in action_labels]
        self.initFlags = [
            'Show_priorities', 'Show_applications', 'Show_parents', 'Show_publications', 'Show_citations',
            'Show_classifications', 'Show_parties', 'Show_legal_events', 'Show_images'
        ]
        
        for btn, flag in zip(self.action_buttons, self.initFlags):
            btn.on_click(lambda b, flag=flag: self.process_with_initFlag(flag))

        # Define process button before calling display_checkboxes
        self.process_button = widgets.Button(description="Process Selected Countries")
        self.process_button.on_click(self.on_process_button_clicked)

        self.process_all_button = widgets.Button(description="Process All Countries")
        self.process_all_button.on_click(self.on_process_all_button_clicked)
        
        # Initialize values
        self.update_doc_number({'new': self.reference_type_widget.value})
        
        display(
            self.reference_type_widget, self.doc_number_widget, self.country_widget, self.kind_widget,
            self.constituents_widget, self.input_widget, self.output_type_widget, self.submit_button, self.output
        )
    
    def update_doc_number(self, change):
        """
        Updates the doc_number widget based on the selected reference type.
        """
        # Clear the output before displaying checkboxes
        with self.output:
            clear_output(wait=True)
        
        # Reset checkboxes when reference type changes
        self.country_checkboxes = []
    
        if change['new'] == 'application':
            self.doc_number_widget.value = '09164213' # '09164213', '13168514', '21958007'
            self.country_widget.value = 'EP'
            self.kind_widget.value = 'A'
            self.constituents_widget.value = None
            self.output_type_widget.value = 'raw'
        elif change['new'] == 'publication':
            self.doc_number_widget.value = '2101496'
            self.country_widget.value = 'EP'
            self.kind_widget.value = 'B1'
            self.constituents_widget.value = 'legal'
            self.output_type_widget.value = 'dataframe'
        else:
            self.doc_number_widget.value = ''
            self.country_widget.value = ''
            self.kind_widget.value = ''
            self.constituents_widget.value = None
            self.output_type_widget.value = 'raw'
    
    def process_with_initFlag(self, flag):
        """
        This method processes the patent tree data using a specific initFlag, 
        which represents different actions (e.g., showing priorities, publications, etc.).
        """
        # Directs the output of the following code to the widget's output display.        
        with self.output:
            # Clears the output from previous actions to provide a clean view.
            clear_output(wait=True)

            # Check if the action is "Show Legal Events" and the reference type is not "publication"
            if flag == "Show_legal_events" and self.reference_type_widget.value != "publication":
                print("Warning: Legal Events can only be retrieved if the Reference Type is set to 'publication'.")
                return  # Stop execution
            
            try:
                # Initializes the TreeProcessor object with the tree, root node, and relevant application data.
                tree_processor = TreeProcessor(
                    tree=self.tree, root=self.root, initFlag=flag, listAPs=self.listAPs,
                    listORAPs=self.listORAPs, df=self.filtered_app_numbers, familyRoot=self.familyRoot
                )
                # Checks if a file exists at the given path where the tree file will be saved. If it does, it deletes the file to ensure fresh processing.
                if os.path.exists(tree_processor.application_tree_file_path):
                    os.remove(tree_processor.application_tree_file_path)
                # Processes the tree file and returns the root node.
                current_root = tree_processor.process_tree("application")
                # Reads and prints the contents of the processed tree file if it exists.
                if os.path.exists(tree_processor.application_tree_file_path):
                    with open(tree_processor.application_tree_file_path, 'r') as f:
                        content = f.read()
                        print(f"Raw content of Application tree file:{content}")
                        # print(f"Application tree contains {len(content.splitlines())} files.\n")  # Alternative line count
                
                # if os.path.exists(tree_processor.priority_tree_file_path):
                #     os.remove(tree_processor.priority_tree_file_path)
                # # Processes the tree file and returns the root node.
                # current_root = tree_processor.process_tree("priority")                
                # if os.path.exists(tree_processor.priority_tree_file_path):
                #     with open(tree_processor.priority_tree_file_path, 'r') as f:          
                #        content = f.read()
                #        print(f"Raw content of Priority tree file:{content}")
                #        # print(f"Priority tree contains {len(content.splitlines())} files.\n")  # Alternative line count                        
                if self.tree:
                    self.display_checkboxes()        
                    display(*self.action_buttons)
                else:
                    print("Failed to process the tree.")
                    
            except Exception as e:
                print(f"Error processing tree with initFlag {flag}: {e}")
                import traceback
                traceback.print_exc()

    def display_checkboxes(self):
        """
        Displays checkboxes for country selection, ensuring old checkboxes are cleared
        while keeping other UI elements like buttons intact.
        """

        # Ensure there's a container to hold the checkboxes
        if not hasattr(self, "checkbox_container"):
            self.checkbox_container = widgets.VBox([])  # Creates an empty container
            
        # Reset record1 to ensure it is always freshly created
        self.record1 = None  
        
        # Checks if record1 exists; if not, it creates a new FamilyRecord object using the current widget values (reference type, document number, country, kind, constituents).
        try:
            self.record1 = FamilyRecord(
                self.reference_type_widget.value,
                self.doc_number_widget.value, 
                self.country_widget.value,
                self.kind_widget.value, 
                [str(self.constituents_widget.value)] if self.reference_type_widget.value in ['application', 'publication'] and self.constituents_widget.value else []
            )
            
            # Check if DropdownCC exists
            if not hasattr(self.record1, 'DropdownCC'):
                print("Error: DropdownCC attribute is missing in FamilyRecord.")
                return

            # Create new checkboxes based on the latest country codes
            self.country_checkboxes = [
                widgets.Checkbox(value=False, description=c) for c in self.record1.DropdownCC if c not in ["EP", "WO"]
            ]
            # Update the container with new checkboxes
            self.checkbox_container.children = self.country_checkboxes

            # print("1. self.checkbox_container_displayed:", self.checkbox_container_displayed)
            # Display the container if not already displayed
            if not hasattr(self, "checkbox_container_displayed") or not self.checkbox_container_displayed:
                # print("2. self.checkbox_container_displayed:", self.checkbox_container_displayed)                
                display(self.checkbox_container, self.process_button, self.process_all_button)
                self.checkbox_container_displayed = True
            elif not self.checkbox_container_displayed:
                # print("3. self.checkbox_container_displayed:", self.checkbox_container_displayed)                    
                # If already displayed, just update the container's children
                display(self.checkbox_container, self.process_button, self.process_all_button)
                
        except Exception as e:
            print(f"Error initializing FamilyRecord: {e}")
            import traceback
            traceback.print_exc()

    def create_and_process_tree(self, selected_countries=None):
        """
        This method creates a patent tree using the TreeCreation class and processes it with the TreeProcessor.
        """        
        try:
            # Creates a TreeCreation object using the patent data.
            self.tree = TreeCreation(db="EPODOC", df=self.filtered_app_numbers)
            
            # Calls the method to create a nested dictionary structure representing the patent tree, and extracts relevant lists of applications and filtered application numbers.
            self.root, self.listAPs, self.listORAPs, self.filtered_app_numbers = self.tree.create_nested_dict(self.filtered_app_numbers, selected_countries)

            # Converts the nested dictionary to a tree structure using TreeNode objects.
            tree_object = TreeNode.dict_to_object(self.tree)

            # Initializes a TreeProcessor object to handle tree processing.
            tree_processor = TreeProcessor(
                tree=tree_object, root=self.root, initFlag=self.initFlag,
                listAPs=self.listAPs, listORAPs=self.listORAPs, df=self.filtered_app_numbers, familyRoot=self.familyRoot
            )

            # Processes the tree and creates a tree file that represents the patent family structure.
            tree_processor.process_tree("application")
            # Reads and prints the content of the processed tree file.
            with open(tree_processor.application_tree_file_path, 'r') as f:
                content = f.read()
                print(f"Raw content of Application tree file:{content}")
                # print(f"Application tree contains {len(content.splitlines())} files.\n")  # Alternative line count

            # tree_processor.process_tree("priority")
            # with open(tree_processor.priority_tree_file_path, 'r') as f:
            #     content = f.read()
            #     print(f"Raw content of Priority tree file:{content}")
            #     # print(f"Priority tree contains {len(content.splitlines())} files.\n")  # Alternative line count
                
            # If the tree is successfully created, it displays the checkboxes and action buttons for further actions.
            if self.tree:
                self.display_checkboxes()
                display(*self.action_buttons)
            else:
                # Catches exceptions during tree processing and returns None values if the process fails.
                print("Failed to process the tree.")
                
            return self.tree, self.root, self.listAPs, self.listORAPs, self.filtered_app_numbers
            
        except Exception as e:
            print(f"Error creating and processing tree in patent_processor method: {e}")
            return None, None, None, None, None

    def process_patent_record(self, selected_countries=None):
        self.checkbox_container_displayed = False        
        with self.output:
            clear_output(wait=True)
            try:
                # Reset record1 to ensure it's recreated with the latest values
                self.record1 = None

                record = FamilyRecord(
                    self.reference_type_widget.value, self.doc_number_widget.value, self.country_widget.value,
                    self.kind_widget.value, [str(self.constituents_widget.value)] if self.reference_type_widget.value == 'publication' and self.constituents_widget.value else [], selected_countries
                )
                
                result = record.process_fami_record(selected_countries)
                if isinstance(result, tuple):
                    self.filtered_app_numbers, _ = result
                    self.familyRoot = record.get_family_root()
                    self.create_and_process_tree(selected_countries)
                else:
                    print("No valid data found. Unable to proceed with tree creation.")

                # Update checkboxes after processing the record
                self.display_checkboxes()
            except Exception as e:
                print(f"Error processing patent record: {e}")
                import traceback
                traceback.print_exc()

    def on_submit_button_clicked(self, b):
        selected_countries = ['EP', 'WO']
        self.process_patent_record(selected_countries)
        display(self.process_all_button)

    def on_process_all_button_clicked(self, b):
        for cb in self.country_checkboxes:
            cb.value = True
        self.on_process_button_clicked(b)
        
    def on_process_button_clicked(self, b):
        """
        This method processes the data for the selected countries when the "Process Selected Countries" button is clicked.
        """
        selected_countries = [cb.description for cb in self.country_checkboxes if cb.value]
        # Gathers the countries selected by the user from the checkboxes.
        if selected_countries:
            self.process_patent_record(selected_countries)
        else:
            print("No countries selected.")
        
