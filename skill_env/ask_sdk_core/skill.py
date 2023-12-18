
import typing

from ask_sdk_model.services import ServiceClientFactory, ApiConfiguration
from ask_sdk_model import ResponseEnvelope

from ask_sdk_runtime.skill import AbstractSkill, RuntimeConfiguration
from ask_sdk_runtime.dispatch import GenericRequestDispatcher
from ask_sdk_runtime.exceptions import AskSdkException
from ask_sdk_runtime.utils import UserAgentManager

from .serialize import DefaultSerializer
from .handler_input import HandlerInput
from .attributes_manager import AttributesManager
from .view_resolvers import TemplateFactory
from .utils import RESPONSE_FORMAT_VERSION, user_agent_info
from .__version__ import __version__

if typing.TYPE_CHECKING:
    from typing import List, Dict, Any
    from ask_sdk_model.services import ApiClient
    from ask_sdk_model import RequestEnvelope, Response
    from ask_sdk_runtime.dispatch_components import (
        GenericRequestMapper, GenericHandlerAdapter, GenericExceptionMapper,
        AbstractRequestInterceptor, AbstractResponseInterceptor)
    from .attributes_manager import AbstractPersistenceAdapter


class SkillConfiguration(RuntimeConfiguration):
    

    def __init__(
            self, request_mappers, handler_adapters,
            request_interceptors=None, response_interceptors=None,
            exception_mapper=None, persistence_adapter=None,
            api_client=None, custom_user_agent=None, skill_id=None):
        
        super(SkillConfiguration, self).__init__(
            request_mappers=request_mappers,
            handler_adapters=handler_adapters,
            request_interceptors=request_interceptors,
            response_interceptors=response_interceptors,
            exception_mapper=exception_mapper)
        self.persistence_adapter = persistence_adapter
        self.api_client = api_client
        self.custom_user_agent = custom_user_agent
        self.skill_id = skill_id


class CustomSkill(AbstractSkill):
    

    def __init__(self, skill_configuration):
        
        self.persistence_adapter = skill_configuration.persistence_adapter
        self.api_client = skill_configuration.api_client
        self.serializer = DefaultSerializer()
        self.skill_id = skill_configuration.skill_id
        self.custom_user_agent = skill_configuration.custom_user_agent
        self.loaders = skill_configuration.loaders
        self.renderer = skill_configuration.renderer

        self.request_dispatcher = GenericRequestDispatcher(
            options=skill_configuration
        )

        UserAgentManager.register_component(
            user_agent_info(sdk_version=__version__))
        if skill_configuration.custom_user_agent is not None:
            UserAgentManager.register_component(
                component_name=skill_configuration.custom_user_agent)

    def supports(self, request_envelope, context):
        
        return 'request' in request_envelope

    def invoke(self, request_envelope, context):
        
        if (self.skill_id is not None and
                request_envelope.context.system.application.application_id !=
                self.skill_id):
            raise AskSdkException("Skill ID Verification failed!!")

        if self.api_client is not None:
            api_token = request_envelope.context.system.api_access_token
            api_endpoint = request_envelope.context.system.api_endpoint
            api_configuration = ApiConfiguration(
                serializer=self.serializer, api_client=self.api_client,
                authorization_value=api_token,
                api_endpoint=api_endpoint)
            factory = ServiceClientFactory(api_configuration=api_configuration)
        else:
            factory = None

        template_factory = TemplateFactory(
            template_loaders=self.loaders,
            template_renderer=self.renderer)

        attributes_manager = AttributesManager(
            request_envelope=request_envelope,
            persistence_adapter=self.persistence_adapter)

        handler_input = HandlerInput(
            request_envelope=request_envelope,
            attributes_manager=attributes_manager,
            context=context,
            service_client_factory=factory,
            template_factory=template_factory)

        response = self.request_dispatcher.dispatch(
            handler_input=handler_input)  # type: Response
        session_attributes = None

        if request_envelope.session is not None:
            session_attributes = (
                handler_input.attributes_manager.session_attributes)

        return ResponseEnvelope(
            response=response, version=RESPONSE_FORMAT_VERSION,
            session_attributes=session_attributes,
            user_agent=UserAgentManager.get_user_agent())
