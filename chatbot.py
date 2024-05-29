from utils.intent_classifier import intent_classifier_parser, intent_classifier_prompt
from utils.warranty_module import warranty_parser, warranty_checker_prompt
from utils.techissue_analyser import tech_issue_analyser_parser, tech_issue_analyser_prompt
from langchain_core.runnables import RunnableParallel
from utils.repair_strategy import repair_parser, repair_strategy_prompt
from utils.replace_strategy import replacement_parser, replacement_strategy_prompt
from utils.tradein_strategy import tradein_parser, tradein_strategy_prompt
from utils.plan_selection import plan_parser, plan_selection_prompt
from utils.user_preference_module import preference_identifier_parser, preference_identifier_prompt
from utils.question_generator import question_generator_parser, question_generator_prompt


import os
from dotenv import load_dotenv

import langchain
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from langchain.globals import set_llm_cache
from langchain.cache import SQLiteCache

set_llm_cache(SQLiteCache(database_path=".langchain_cache.db"))

langchain.debug = False  # set verbose mode to True to show more execution details

load_dotenv()

langchain_llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("YOUR_AZURE_ENDPOINT"),
    api_key=os.getenv("AZURE_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    openai_api_type="azure",
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    verbose=True,
)

# Or use openai's model
langchain_llm = ChatOpenAI(
    base_url=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o",
    verbose=True,
)

class Chatbot:
    def __init__(self):
        # Inforamtion about the conversation
        self.conversation_turn = 0
        self.greeting = "Hello! This is repairing bot. I can help you diagnose your tablet and provide you a repairing suggestion. How can I help you today?"
        self.broken_places = []
        self.user_warranty = "unsure"
        self.repair_plan = ""
        self.user_preference = ""
        self.chat_history = []
        self.information_collection_turns = 0


        # The chains for the chatbot

        self.intent_classifier_chain = intent_classifier_prompt | langchain_llm | intent_classifier_parser
        self.warranty_checker_chain = warranty_checker_prompt | langchain_llm | warranty_parser
        self.tech_issue_analyser_chain = tech_issue_analyser_prompt | langchain_llm | tech_issue_analyser_parser
        self.user_preference_chain = preference_identifier_prompt | langchain_llm | preference_identifier_parser

        # The chains for intent classification
        self.intent_classifier_chain_all = RunnableParallel(
            service_intent = self.intent_classifier_chain,
            user_preference = self.user_preference_chain,
        )

        # The tot structure for plan generation
        repair_strategy_chain = repair_strategy_prompt | langchain_llm | repair_parser
        replacement_strategy_chain = (
            replacement_strategy_prompt | langchain_llm | replacement_parser
        )
        tradein_strategy_chain = tradein_strategy_prompt | langchain_llm | tradein_parser

        self.tot_generater = RunnableParallel(repair_plan = repair_strategy_chain, replace_plan = replacement_strategy_chain, tradein_plan = tradein_strategy_chain)

        self.tot_scorer = plan_selection_prompt | langchain_llm | plan_parser
        

    def update_chat_history(self, user_input: str = "", ai_input: str = ""):
        self.chat_history.append({
            "user": user_input,
            "ai": ai_input
        })
        self.conversation_turn += 1

    def repair_plan_generation(self):
        pass

    def interact(self, user_input = ""):
        if self.conversation_turn == 0:
            self.update_chat_history(user_input=user_input, ai_input=self.greeting)
            return self.greeting
        
        output = self.intent_classifier_chain_all.invoke({
            "user_input": user_input
        })
        service_intent = output["service_intent"]["want_to_repair"]
        ai_utterance = output["service_intent"]["utterance"]
        self.user_preference = output["user_preference"]["user_preference"]
        if service_intent.lower() == "end":
            self.update_chat_history(user_input=user_input, ai_input=ai_utterance)
            return ai_utterance
        
        # If the user does not want to end the conversation, try to find out technical infomation.
        if self.information_collection_turns == 0:
            ai_utterance = "Could you please provide me more information about the issue of your tablet? And when did you purchased this item?"
            self.update_chat_history(user_input=user_input, ai_input=ai_utterance)
            self.information_collection_turns += 1
            return ai_utterance
        elif self.information_collection_turns <= 2:
            tech_issue_warranty_chain = RunnableParallel(
                tech_issue = self.tech_issue_analyser_chain,
                warranty = self.warranty_checker_chain,
            )
            output = tech_issue_warranty_chain.invoke({
                "user_input": user_input,
                "chat_history": self.chat_history
            })

            broken_places = output["tech_issue"]["tech_issue"]
            # update the broken places by taking the union of the broken places
            self.broken_places = list(set(self.broken_places + broken_places))
            warranty = output["warranty"]["Warranty"]
            # update the warranty with new information, ignore the "unsure" case
            if warranty.lower() != "unsure":
                self.user_warranty = warranty

            information_to_collect = []
            if self.broken_places == []:
                information_to_collect.append("broken parts")
            if self.user_warranty == "unsure":
                information_to_collect.append("is user's product have warranty")
            if information_to_collect != []:
                question_generation_chain = question_generator_prompt | langchain_llm | question_generator_parser
                output = question_generation_chain.invoke({
                    "required_information": information_to_collect
                })
                ai_utterance = output["utterance"]
                self.update_chat_history(user_input=user_input, ai_input=ai_utterance)
                self.information_collection_turns += 1
                return ai_utterance
            else:
                ai_utterance = "I have collected all the information. Let me think about the repairing plan for you. Give me a second."
                self.update_chat_history(user_input=user_input, ai_input=ai_utterance)
                self.information_collection_turns += 1
                
                return ai_utterance
                



            self.update_chat_history(user_input=user_input, ai_input=ai_utterance)
            self.information_collection_turns += 1
            return ai_utterance
        
        
                

