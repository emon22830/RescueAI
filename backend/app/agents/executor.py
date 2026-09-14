"""Runs approved actions against the real integrations. No LLM involved.

This is the last code that runs before we touch somebody else's workspace, so the
approval check lives here rather than only in the caller: an action that is not
`approved` never reaches an integration.

`ACTION_TYPES` is the one list of what this system can do to a connected app. The
recovery prompt is generated from it, the dashboard's composer is offered it, and
`execute` dispatches to it — so a type cannot exist in one of those three places and
not the others.
"""

from typing import Literal

from pydantic import BaseModel

from app.agents.state import PlannedAction, Source
from app.integrations import (
    asana, calendar, drive, github, gmail, jira, linear, notion, slack, trello,
)

INTEGRATIONS = {
    "slack": slack,
    "gmail": gmail,
    "drive": drive,
    "linear": linear,
    "jira": jira,
    "asana": asana,
    "trello": trello,
    "github": github,
    "notion": notion,
    "calendar": calendar,
}

# What a step does, in the words a project manager would use. The UI groups by this.
Verb = Literal["add", "update", "delegate", "close", "message"]


class ActionType(BaseModel):
    """One thing the agent — or a user at the dashboard — can ask an app to do."""

    integration: Source
    type: str
    verb: Verb
    label: str  # what the button says
    target_label: str  # what `target` means for this type
    value_label: str  # what `params.value` means for this type
    guidance: str  # the line the recovery prompt shows the model


ACTION_TYPES: list[ActionType] = [
    # --- Slack: telling people ---
    ActionType(
        integration="slack", type="post_message", verb="message",
        label="Post a message", target_label="Channel (#payments)",
        value_label="What to say",
        guidance="target = the channel (#payments), value = the message to post",
    ),
    # --- Linear: the work itself ---
    ActionType(
        integration="linear", type="create_issue", verb="add",
        label="Create an issue", target_label="Issue title",
        value_label="What the issue is for",
        guidance="target = the issue title, value = its description. "
                 "Optional params: team (key like PAY), assignee, due_date (YYYY-MM-DD)",
    ),
    ActionType(
        integration="linear", type="update_issue", verb="update",
        label="Update an issue", target_label="Issue (PAY-124)",
        value_label="The change to record",
        guidance="target = issue identifier (PAY-124), value = the change to record. "
                 "Optional params: state, assignee, due_date",
    ),
    ActionType(
        integration="linear", type="assign_task", verb="delegate",
        label="Assign an issue", target_label="Issue (PAY-124)",
        value_label="Who to assign it to",
        guidance="target = issue identifier, value = the person's name or email",
    ),
    ActionType(
        integration="linear", type="update_due_date", verb="update",
        label="Change a due date", target_label="Issue (PAY-124)",
        value_label="New due date (YYYY-MM-DD)",
        guidance="target = issue identifier, value = the new date as YYYY-MM-DD",
    ),
    ActionType(
        integration="linear", type="comment_issue", verb="message",
        label="Comment on an issue", target_label="Issue (PAY-124)",
        value_label="The comment",
        guidance="target = issue identifier, value = the comment to post",
    ),
    ActionType(
        integration="linear", type="close_issue", verb="close",
        label="Close an issue", target_label="Issue (PAY-124)",
        value_label="Closing state (optional, e.g. Done or Canceled)",
        guidance="target = issue identifier, value = the closing state name, "
                 "or empty for the team's default done state",
    ),
    # --- GitHub: the code side of the same work ---
    ActionType(
        integration="github", type="create_issue", verb="add",
        label="Open an issue", target_label="Issue title", value_label="The issue body",
        guidance="target = the issue title, value = the issue body",
    ),
    ActionType(
        integration="github", type="comment_issue", verb="message",
        label="Comment on an issue", target_label="Issue number (124)",
        value_label="The comment",
        guidance="target = the issue number (124), value = the comment to post",
    ),
    ActionType(
        integration="github", type="assign_issue", verb="delegate",
        label="Assign an issue", target_label="Issue number (124)",
        value_label="GitHub usernames, comma separated",
        guidance="target = the issue number, value = GitHub usernames, comma separated",
    ),
    ActionType(
        integration="github", type="close_issue", verb="close",
        label="Close an issue", target_label="Issue number (124)",
        value_label="Closing comment (optional)",
        guidance="target = the issue number, value = a closing comment, or empty",
    ),
    # --- Jira: the same work, where most of the industry actually tracks it ---
    ActionType(
        integration="jira", type="create_issue", verb="add",
        label="Create an issue", target_label="Issue summary",
        value_label="The description",
        guidance="target = the issue summary, value = its description. "
                 "Optional params: project (key like PAY), issue_type, due_date (YYYY-MM-DD)",
    ),
    ActionType(
        integration="jira", type="assign_task", verb="delegate",
        label="Assign an issue", target_label="Issue key (PAY-124)",
        value_label="Who to assign it to",
        guidance="target = the issue key (PAY-124), value = the person's name or email",
    ),
    ActionType(
        integration="jira", type="update_due_date", verb="update",
        label="Change a due date", target_label="Issue key (PAY-124)",
        value_label="New due date (YYYY-MM-DD)",
        guidance="target = the issue key, value = the new date as YYYY-MM-DD",
    ),
    ActionType(
        integration="jira", type="comment_issue", verb="message",
        label="Comment on an issue", target_label="Issue key (PAY-124)",
        value_label="The comment",
        guidance="target = the issue key, value = the comment to post",
    ),
    ActionType(
        integration="jira", type="close_issue", verb="close",
        label="Close an issue", target_label="Issue key (PAY-124)",
        value_label="Transition name (optional, e.g. Done)",
        guidance="target = the issue key, value = the workflow transition to use, "
                 "or empty for the first one that leads to Done",
    ),
    # --- Asana ---
    ActionType(
        integration="asana", type="create_task", verb="add",
        label="Create a task", target_label="Task name", value_label="The notes",
        guidance="target = the task name, value = its notes. "
                 "Optional params: project, due_date (YYYY-MM-DD)",
    ),
    ActionType(
        integration="asana", type="assign_task", verb="delegate",
        label="Assign a task", target_label="Task id", value_label="Who to assign it to",
        guidance="target = the task id, value = the person's name",
    ),
    ActionType(
        integration="asana", type="update_due_date", verb="update",
        label="Change a due date", target_label="Task id",
        value_label="New due date (YYYY-MM-DD)",
        guidance="target = the task id, value = the new date as YYYY-MM-DD",
    ),
    ActionType(
        integration="asana", type="comment_task", verb="message",
        label="Comment on a task", target_label="Task id", value_label="The comment",
        guidance="target = the task id, value = the comment to post",
    ),
    ActionType(
        integration="asana", type="close_task", verb="close",
        label="Complete a task", target_label="Task id", value_label="Not used",
        guidance="target = the task id; value is ignored",
    ),
    # --- Trello ---
    ActionType(
        integration="trello", type="create_card", verb="add",
        label="Create a card", target_label="Card name", value_label="The description",
        guidance="target = the card name, value = its description. "
                 "Required param: list (the id of the list to add it to). "
                 "Optional param: due_date",
    ),
    ActionType(
        integration="trello", type="update_due_date", verb="update",
        label="Change a due date", target_label="Card id",
        value_label="New due date (YYYY-MM-DD)",
        guidance="target = the card id, value = the new date as YYYY-MM-DD",
    ),
    ActionType(
        integration="trello", type="comment_card", verb="message",
        label="Comment on a card", target_label="Card id", value_label="The comment",
        guidance="target = the card id, value = the comment to post",
    ),
    ActionType(
        integration="trello", type="close_card", verb="close",
        label="Archive a card", target_label="Card id", value_label="Not used",
        guidance="target = the card id; value is ignored",
    ),
    # --- Notion ---
    ActionType(
        integration="notion", type="create_page", verb="add",
        label="Create a page", target_label="Page title", value_label="The page text",
        guidance="target = the page title, value = its text. "
                 "Required param: parent (the id of the page to create it under)",
    ),
    ActionType(
        integration="notion", type="comment_page", verb="message",
        label="Comment on a page", target_label="Page id", value_label="The comment",
        guidance="target = the page id, value = the comment to post",
    ),
    # --- Gmail ---
    ActionType(
        integration="gmail", type="send_email", verb="message",
        label="Send an email", target_label="Recipient's email address",
        value_label="What to tell them",
        guidance="target = the recipient's email address, value = what to tell them. "
                 "Optional param: subject",
    ),
    # --- Calendar ---
    ActionType(
        integration="calendar", type="create_event", verb="add",
        label="Book a meeting", target_label="Attendee emails, comma separated",
        value_label="Title and purpose",
        guidance="target = attendee emails, comma separated, value = title and purpose. "
                 "Optional params: start (ISO 8601), minutes",
    ),
    ActionType(
        integration="calendar", type="update_event", verb="update",
        label="Reschedule a meeting", target_label="Event id",
        value_label="What is changing",
        guidance="target = the event id, value = what is changing. "
                 "Optional params: start (ISO 8601), minutes, summary",
    ),
    ActionType(
        integration="calendar", type="cancel_event", verb="close",
        label="Cancel a meeting", target_label="Event id",
        value_label="Why it is cancelled (optional)",
        guidance="target = the event id, value = why it is cancelled",
    ),
]

# The apps an approved action can actually be executed against. Drive collects only.
WRITE_TARGETS = {action.integration for action in ACTION_TYPES}


def types_for(integrations: list[str]) -> list[ActionType]:
    """Everything executable against the apps a project has actually connected."""
    return [action for action in ACTION_TYPES if action.integration in integrations]


def find_type(integration: str, type_: str) -> ActionType | None:
    return next(
        (a for a in ACTION_TYPES if a.integration == integration and a.type == type_), None
    )


class NotApproved(RuntimeError):
    """Someone tried to execute an action a human has not approved."""


def execute(action: PlannedAction, status: str) -> str:
    """Perform one approved action and return the integration's own result line.

    `status` is the action's status in the database at the moment of execution.
    """
    if status != "approved":
        raise NotApproved(f"Action is '{status}', not approved — nothing was executed")

    integration = INTEGRATIONS[action.integration]
    return integration.execute_action(action)
