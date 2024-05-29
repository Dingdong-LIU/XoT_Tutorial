from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    FewShotChatMessagePromptTemplate,
)
from langchain_core.messages import SystemMessage


# Make a parser for the response
class Warranty(BaseModel):
    Analysis: str = Field(description="AI's analysis of the current situation")
    Warranty: str = Field(description="Whether the use's product have a warranty")
    Utterance: str = Field(description="AI's response to the user")


warranty_parser = JsonOutputParser(pydantic_object=Warranty)

# few shot cot exmaples
warranty_checker_examples = [
    {
        "ai_question": "When did you purchase this item?",
        "human_response": "A month ago",
        "ai_response": "Analysis: Let's think step by step. All products come with a 90-day warranty since purchase. A month is within the 90-day time span. The product must have warranty. Warranty: Yes. Utterance: Great! Your product has warranty.",
    },
    {
        "ai_question": "When did you purchase this item?",
        "human_response": "Last year.",
        "ai_response": "Analysis: Let's think step by step. All products come with a 90-day warranty. A year is more than this time span. However, we are not sure if the user purchased additional warranty. We are not sure if the product has warranty. Warranty: Unsure. Utterance: Did you purchase additional warranty?",
    },
]

# define the a fewshot example format
warranty_checker_example_template = ChatPromptTemplate.from_messages(
    [
        ("ai", "{ai_question}"),
        ("human", "{human_response}"),
        ("ai", "{ai_response}"),
    ]
)

# convert to the fewshot example format
warranty_checker_fewshot_examples = FewShotChatMessagePromptTemplate(
    example_prompt=warranty_checker_example_template,
    examples=warranty_checker_examples,
)


warranty_checker_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="You are a helpful agent that help to decide if a product is out of warranty. Note that all product come with a 90-day warranty since purchase. Customer can also purchase additional warranty that extends it to 2 years. Today is May 20th, 2024. Reply if the product has warranty or not. If the product has warranty, reply 'Yes'. If the product does not have warranty, reply 'No'. If you are unsure, reply 'Unsure'."
        ),
        warranty_checker_fewshot_examples,
        HumanMessagePromptTemplate(
            prompt=PromptTemplate(
                template="{user_input}\n{format_instructions}",
                input_variables=["user_input"],
                partial_variables={
                    "format_instructions": warranty_parser.get_format_instructions()
                },
            )
        ),
    ]
)


