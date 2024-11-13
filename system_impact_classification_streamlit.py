import streamlit as st
import os
from io import StringIO
from typing import List, Optional, Annotated
from custom_rag import get_equipment_scores_sync

#============================================================================================
#          Function To get the equipement group and fetch the hiostorial values for criterias
#=============================================================================================

def node_rag(user_equipment):
    """Given human equipment find the most similar equipment group and return probs row wih the highest similarity
    """
    
    print('-----------Node RAG-------------------')
    
    print(f"RAG for input: {user_equipment}")
    df_equipment_score = get_equipment_scores_sync(user_equipment=user_equipment)
    print("RAG Output:")
    print(df_equipment_score)

    if df_equipment_score.empty:
        return None

    else:
        value_8a = True if df_equipment_score['Criteria 8a'].values[0]>0.5 else False
        print(f"According to historical data 'Criteria 8a' is : {value_8a}")
        
        return {'df_output': df_equipment_score,  'criteria_8a_status': value_8a }    





# Define the questions
questions = [
    "Question-1: Is the equipment operational?",
    "Question-2: Is the equipment calibrated?",
    "Question-3: Has the equipment passed safety inspection?",
    "Question-4: Is the equipment in good physical condition?",
]

# Initialize session state variables
if "question_index" not in st.session_state:
    st.session_state.question_index = 0  # Track the current question index
if "ask_question" not in st.session_state:
    st.session_state.ask_question = False  # Flag to check if we should ask questions
if "messages" not in st.session_state:
    st.session_state.messages = []  # Store question-answer pairs
if "equipment_name" not in st.session_state:
    st.session_state.equipment_name = ""  # Store equipment name
if "continue_traversal" not in st.session_state:
    st.session_state.continue_traversal = True  # Flag to check if need to ask further question or not
if "criteria_values" not in st.session_state:
    st.session_state.criteria_values = {}     # Store the criteria values

# Equipment name input
equipment_name = st.text_input("Enter the Equipment Name:")

# Check if equipment name exists in sample data
if equipment_name:
    st.session_state.equipment_name = equipment_name
    st.header("Equipment name is: {}".format(equipment_name))

    # If criteria values already fetched in previous step, display the table
    if st.session_state.criteria_values:
        st.write("Criteria Values :")
        st.dataframe(st.session_state.criteria_values['df_output'])

    
    ## Get the criterias and equipment name from the data if it is not already fetched from LLM
    if not st.session_state.criteria_values:
        
        #============================================================================
        # Calling the LLM Chain to get the group name and values for criteria 1 to 8a
        #============================================================================
        with st.spinner('Wait for it...'):
            criteria_output = node_rag(equipment_name)
        st.success("Done!")
        
        # If there is no matching equipment in the historiacal dataset, stop the flow and exit
        if criteria_output == None:
            st.write("Equipment Not found")
            st.stop()
            # st.rerun()

        # If criteria values are present in the dataset for this equipment, then store these valuese in session_state 
        if criteria_output:
            st.session_state.criteria_values = criteria_output
            st.session_state.equipment_name = list(criteria_output['df_output']['equipment_name'])[0]


        # check if we need to ask questions, set ask_question flag is True and 
        # set the question index for the first querstion in next ieteration and rerun the app
        if criteria_output['criteria_8a_status'] == True:
            if not st.session_state.ask_question:  # Only set it once
                st.session_state.ask_question = True
                st.session_state.question_index = 0  # Reset question index for new equipment
                st.rerun()  # Trigger rerun to start asking questions
        else:

            # It means 8a --> False, then no need to ask questions, we just need to display the fetched table - critera values
            st.write("No need to ask further Questions..")
            st.session_state.ask_question = False
            st.markdown("Final Criteria --")
            st.dataframe(st.session_state.criteria_values['df_output'])



# Ask questions if ask_question flag is True from the previous interaction -- 8a is True
if st.session_state.ask_question and st.session_state.ask_question:

    # Display previous question-answer pairs
    for msg in st.session_state.messages:
        st.write(f"{msg['question']}")
        st.write(f"Answer: {msg['answer']}")

    # Ask the next question if available 
    # (continue_traversal flag tells us wether we need to further traverse in the Tree or we reached to End)
    if st.session_state.continue_traversal:
        current_question = questions[st.session_state.question_index]
        st.write(f"{current_question}")
        
        # Display a text input for the answer
        user_response = st.chat_input("Enter Yes or No:")
        
        # Process response
        if user_response:
            # Save question-answer pair to messages
            st.session_state.messages.append({
                "question": current_question,
                "answer": user_response
            })

            ### Tree Traversal--> based on the user input and tree --> we can decide which question need to ask next

            if st.session_state.question_index == 0 and user_response == "No".lower():
                st.session_state.continue_traversal = False
                st.write("8b is False...")
                st.session_state.criteria_values['df_output']['Criteria 8b'] = 0

            elif st.session_state.question_index == 0 and user_response.lower() == "yes":
                st.session_state.question_index = 1
                st.rerun()

            elif st.session_state.question_index == 1 and user_response.lower() == "no":
                st.session_state.question_index = 2
                st.rerun()

            elif st.session_state.question_index == 1 and user_response.lower() == "yes":
                st.session_state.question_index = 3
                st.rerun()

            elif st.session_state.question_index == 2 and user_response.lower() == "no":
                st.session_state.continue_traversal = False
                st.write("8b is False...")
                st.session_state.criteria_values['df_output']['Criteria 8b'] = 0


            elif st.session_state.question_index == 2 and user_response.lower() == "yes":
                st.session_state.continue_traversal = False
                st.write("8b is True...")
                st.session_state.criteria_values['df_output']['Criteria 8b'] = 1


            elif st.session_state.question_index == 3 and user_response.lower() == "yes":
                st.session_state.continue_traversal = False
                st.write("8b is True...")
                st.session_state.criteria_values['df_output']['Criteria 8b'] = 1

                
            elif st.session_state.question_index == 3 and user_response.lower() == "no":
                st.session_state.continue_traversal = False
                st.write("8b is False...")
                st.session_state.criteria_values['df_output']['Criteria 8b'] = 0

    else:
        # Display summary after all questions are answered, it means we reached to the leaf node of the tree
        st.subheader("All questions completed. Here is a summary:")
        for msg in st.session_state.messages:
            st.write(f"{msg['question']}")
            st.write(f"Answer: {msg['answer']}")

        st.markdown("Final Criteria --")
        st.dataframe(st.session_state.criteria_values['df_output'])

# else:
    # st.write("No questions to ask, as conditions were not met.")

