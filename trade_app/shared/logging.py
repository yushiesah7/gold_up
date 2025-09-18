from __future__ import annotations

import logging

import structlog


def setup_logging(
    reset_handlers: bool = True,
    console_output: bool = True,
    json_format: bool = False,
) -> None:
    if reset_handlers:
        for h in logging.root.handlers[:]:
            logging.root.removeHandler(h)
    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
    ]
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    structlog.configure(processors=processors)
    logging.basicConfig(level=logging.INFO)


def get_logger(name: str):  # 型は環境により異なるため明示は省略
    return structlog.get_logger(name)
