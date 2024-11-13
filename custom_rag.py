import os
import pandas as pd
# from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser 
from config import config

load_dotenv()

llm = AzureChatOpenAI(
    temperature=0,
    openai_api_version=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version= os.getenv("AZURE_OPENAI_API_VERSION"))


def get_rag_chain():
    """Method that generate a rag chain on prompt pandas df. Be sure pipeline_etl.py has been executed to generate table dependencies. 
    Returns:
        _type_: _description_
    """
    # Load data sources
    path_map_equipment_groups = os.path.join(config['folder_data_processed'], config['filename_map_equipment_groups'])
    df_map_equipment_groups = pd.read_csv(path_map_equipment_groups)


    # Parse data on string format
    str_equipment_group_categories = ", ".join(df_map_equipment_groups['equipment_group_name'].values)
    str_map_equipment_groups = df_map_equipment_groups.to_string(index=False)

    # LLM chain builder prompt + LLM + parser
    class EquipmentGroupName(BaseModel):
        """
        This class is going to capture the classification result of 'New equipment' on 'equipment_group_name categories' and the classification score.
        """
        equipment_group_name : str = Field(description="Classified category from equipment_group_name") # default='Unknown'
        new_equipment: str  = Field(description="Equipment name from 'New quipment' that belong to equipment_group_name")
        classification_score: int = Field(ge=0, le=100, description="Confidence level of equipment_group_name classification", default=0)

    output_parser = PydanticOutputParser(pydantic_object = EquipmentGroupName)
    output_format_instructions = output_parser.get_format_instructions()

    prompt_template = """You are an expert in manufacturing, your goal is to classify new equipment into an existing equipment group.
    Be flexible and consider that the equipment name on 'New equipment' could have word variations like plural, synonym or misspelling.
    'New equipment' should match one of the following 'equipment_group_name categories': {equipment_group_categories}.

    {output_format_instructions}

    'New equipment':
    {user_equipment}

    For the classification task, take into consideration similar names on 'equipments' column on the following table:
    {map_equipment_groups}

    """

    prompt = PromptTemplate(template=prompt_template, variables = {'user_equipment','map_equipment_groups', 'output_format_instructions', 'equipment_group_categories'}) # @todo add cols as variables

    partial_prompt =  prompt.partial(map_equipment_groups=str_map_equipment_groups,
                                     output_format_instructions=output_format_instructions,
                                     equipment_group_categories=str_equipment_group_categories
                                     )

    chain = partial_prompt | llm | output_parser
    #chain = prompt | llm | output_parser

    return chain


# async def get_equipment_scores(user_equipment:str) -> pd.DataFrame:
#     """Use LLM to find equipment group given user_equipment
#     Load equipment probs table and return value that matches equipment group
 
#     Args:
#         user_equipment (str): _description_

#     Returns:
#         pd.DataFrame: _description_
#     """

#     #Load data sources
#     path_equipment_group_probs = os.path.join(config['folder_data_processed'], config['filename_equipment_group_probs'])
#     df_equipment_group_probs = pd.read_csv(path_equipment_group_probs)

#     # Load and call chain
#     chain = get_rag_chain()
#     result = await chain.ainvoke({'user_equipment': user_equipment})
#     print('Equipment category analysis: ', result)

#     # Parse tables to Get equiment scores
#     df_equipment_probs = df_equipment_group_probs.copy()
#     equipment_group_name = result.equipment_group_name
#     df_equipment_probs = df_equipment_probs.loc[df_equipment_probs['equipment_group_name']==equipment_group_name]
#     df_equipment_probs['equipment_name'] = user_equipment
    
#     return df_equipment_probs

def get_equipment_scores_sync(user_equipment:str) -> pd.DataFrame:
    """Use LLM to find equipment group given user_equipment
    Load equipment probs table and return value that matches equipment group
 
    Args:
        user_equipment (str): _description_

    Returns:
        pd.DataFrame: _description_
    """

    #Load data sources
    path_equipment_group_probs = os.path.join(config['folder_data_processed'], config['filename_equipment_group_probs'])
    # print("File path to read csv file-----")
    # print(path_equipment_group_probs)
    df_equipment_group_probs = pd.read_csv(path_equipment_group_probs)

    # Load and call chain
    chain = get_rag_chain()
    result = chain.invoke({'user_equipment': user_equipment})
    # print('Equipment category analysis: ', result)

    # Parse tables to Get equiment scores
    df_equipment_probs = df_equipment_group_probs.copy()
    equipment_group_name = result.equipment_group_name
    df_equipment_probs = df_equipment_probs.loc[df_equipment_probs['equipment_group_name']==equipment_group_name]
    df_equipment_probs['equipment_name'] = user_equipment
    
    return df_equipment_probs


if __name__=="__main__":
    user_equipment = 'Cooler'
    print(f"RAG for input: {user_equipment}")
    df_equipment_score = get_equipment_scores_sync(user_equipment=user_equipment)
    print("RAG Output:",df_equipment_score)
