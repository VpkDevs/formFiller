from typing import Optional
from .di_container import Container
from .config import AppConfig
from .events import EventBus
from .exceptions import FormAutofillerError

class FormAutofillerApp:
    \"\"\"Main application class for the Form Autofiller Pro application.\"\"\"
    def __init__(self, config_path: Optional[str] = None):
        \"\"\"Initialize the application with the given configuration path.
        
        Args:
            config_path (Optional[str]): Path to the configuration file. If None, default configuration is used.
        \"\"\"
        # Initialize configuration
        self.config = AppConfig.load(config_path) if config_path else AppConfig.get_default()
        
        # Set up dependency injection
        self.container = Container()
        self.container.config.from_dict({
            "security": self.config.security.__dict__,
            "state": self.config.state.__dict__,
            "form_filler": self.config.form_filler.__dict__
        })
        
        # Initialize event bus
        self.event_bus = EventBus()
        
        # Wire up dependencies
        self.container.wire(modules=[".ui", ".form_filling", ".profiles"])
        
    def run(self):
        \"\"\"Run the application, initializing the UI and handling errors.\"\"\"
        try:
            # Initialize UI
            ui = self.container.ui()
            ui.run()
        except FormAutofillerError as e:
            self.container.logger().error(f"Application error: {e}")
            # Show error dialog to user
        except Exception as e:
            self.container.logger().critical(f"Unexpected error: {e}")
            # Show critical error dialog