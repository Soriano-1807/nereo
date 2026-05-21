import os

from src.ui.app import app


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8050")),
        debug=False,
        dev_tools_ui=False,
    )
