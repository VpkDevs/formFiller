from dependency_injector import containers, providers
from logging import Logger
from typing import Dict, Any

class Container(containers.DeclaratorContainer):
    config = providers.Configuration()
    
    # Core services
    logger = providers.Singleton(Logger, name="form_autofiller")
    
    security_manager = providers.Singleton(
        'security.encryption.SecurityManager',
        key_file=config.security.key_file
    )
    
    state_manager = providers.Singleton(
        'state.StateManager',
        auto_save_interval=config.state.auto_save_interval,
        logger=logger
    )
    
    validator = providers.Singleton(
        'validation.DataValidator',
        logger=logger
    )
    
    # Feature modules
    profile_manager = providers.Singleton(
        'profiles.ProfileManager',
        state_manager=state_manager,
        security_manager=security_manager,
        logger=logger
    )
    
    form_filler = providers.Singleton(
        'form_filling.FormFiller',
        validator=validator,
        logger=logger
    )