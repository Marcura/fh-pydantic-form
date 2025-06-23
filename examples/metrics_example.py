import datetime
import logging
from enum import Enum
from typing import List, Optional

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field

from fh_pydantic_form import (
    MetricEntry,
    PydanticForm,
    list_manipulation_js,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        list_manipulation_js(),
    ],
    pico=False,
    live=True,
)


# ============================================================================
# Simple Data Model for Metrics Demo
# ============================================================================


class Priority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class TaskStatus(Enum):
    TODO = "Todo"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    DONE = "Done"


class ProjectTask(BaseModel):
    """A simple project task model to demonstrate metrics"""

    title: str = Field(description="Task title")
    description: str = Field(description="Detailed task description")
    priority: Priority = Field(description="Task priority level")
    status: TaskStatus = Field(description="Current task status")
    assigned_to: Optional[str] = Field(None, description="Assignee name")

    # Time tracking
    estimated_hours: float = Field(description="Estimated completion time in hours")
    actual_hours: Optional[float] = Field(
        None, description="Actual time spent in hours"
    )

    # Dates
    due_date: datetime.date = Field(description="Task due date")
    completed_date: Optional[datetime.date] = Field(None, description="Completion date")

    # Sub-tasks
    subtasks: List[str] = Field(default_factory=list, description="List of subtasks")

    # Quality metrics
    complexity_score: float = Field(description="Task complexity (1-10 scale)")
    quality_score: Optional[float] = Field(
        None, description="Quality rating (1-5 scale)"
    )


# ============================================================================
# Sample Data with Realistic Task Information
# ============================================================================

sample_task = ProjectTask(
    title="Implement User Authentication System",
    description="Build a secure authentication system with JWT tokens, password hashing, and role-based access control",
    priority=Priority.HIGH,
    status=TaskStatus.IN_PROGRESS,
    assigned_to="Alice Johnson",
    estimated_hours=24.0,
    actual_hours=18.5,
    due_date=datetime.date(2024, 2, 15),
    completed_date=None,
    subtasks=[
        "Design database schema for users",
        "Implement password hashing",
        "Create JWT token system",
        "Build login/logout endpoints",
        "Add role-based middleware",
    ],
    complexity_score=8.5,
    quality_score=4.2,
)


# ============================================================================
# Comprehensive Metrics Dictionary
# ============================================================================

# This demonstrates various types of metrics you might want to track
task_metrics = {
    # Overall task metrics
    "title": MetricEntry(
        metric=0.95,
        comment="Title is clear and descriptive, minor improvement could be made",
    ),
    "description": MetricEntry(
        metric=0.88,
        comment="Good detail level, covers main requirements but could specify security standards",
    ),
    # Enum field metrics
    "priority": MetricEntry(
        metric=1.0,
        comment="Priority correctly set as HIGH for security-critical feature",
    ),
    "status": MetricEntry(
        metric=0.75, comment="Status is current but should be updated more frequently"
    ),
    # Assignment and planning metrics
    "assigned_to": MetricEntry(
        metric=1.0, comment="Assigned to experienced developer with security background"
    ),
    "estimated_hours": MetricEntry(
        metric=0.80,
        comment="Estimation seems reasonable but might be slightly low for security features",
    ),
    "actual_hours": MetricEntry(
        metric=0.92, comment="Good progress, slightly ahead of schedule"
    ),
    # Date tracking metrics
    "due_date": MetricEntry(
        metric=0.85, comment="Deadline is achievable but tight given complexity"
    ),
    "completed_date": MetricEntry(
        metric=0.0, comment="Task not yet completed - tracking for timeline analysis"
    ),
    # List field metrics (subtasks)
    "subtasks": MetricEntry(
        metric=0.90, comment="Well-broken down subtasks, covers main components"
    ),
    "subtasks[0]": MetricEntry(
        metric=1.0, comment="Database schema is properly prioritized first"
    ),
    "subtasks[1]": MetricEntry(
        metric=0.95, comment="Password hashing is critical - good inclusion"
    ),
    "subtasks[2]": MetricEntry(
        metric=0.85,
        comment="JWT implementation subtask could be more specific about token refresh",
    ),
    "subtasks[3]": MetricEntry(
        metric=0.90, comment="Endpoint creation is well-defined"
    ),
    "subtasks[4]": MetricEntry(
        metric=0.80,
        comment="Role-based middleware subtask could specify permission levels",
    ),
    # Quality and complexity metrics
    "complexity_score": MetricEntry(
        metric=0.85, comment="Complexity rating aligns with security requirements"
    ),
    "quality_score": MetricEntry(
        metric=0.84,
        comment="Quality score is good but could be higher with better documentation",
    ),
}

# Alternative metrics showing different scenarios
alternative_metrics = {
    "title": MetricEntry(
        metric=0.40,
        comment="⚠️ Title is too vague - should specify authentication method",
    ),
    "priority": MetricEntry(
        metric=0.60, comment="⚠️ Priority might be underestimated for security feature"
    ),
    "estimated_hours": MetricEntry(
        metric=0.30,
        comment="❌ Significantly underestimated - security features typically require 40+ hours",
    ),
    "subtasks": MetricEntry(
        metric=0.50,
        comment="⚠️ Missing important subtasks: security testing, documentation, error handling",
    ),
    "quality_score": MetricEntry(
        metric=0.95, comment="✅ Excellent quality score - well implemented"
    ),
}


# ============================================================================
# Create Forms with Different Metric Scenarios
# ============================================================================

# Form showing good metrics (high scores)
good_metrics_form = PydanticForm(
    form_name="good_metrics_task",
    model_class=ProjectTask,
    initial_values=sample_task,
    disabled=True,  # Read-only for metrics display
    spacing="normal",
    metrics_dict=task_metrics,
)

# Form showing areas for improvement (mixed scores)
improvement_metrics_form = PydanticForm(
    form_name="improvement_metrics_task",
    model_class=ProjectTask,
    initial_values=sample_task,
    disabled=True,  # Read-only for metrics display
    spacing="normal",
    metrics_dict=alternative_metrics,
)

# Editable form without metrics for comparison
editable_form = PydanticForm(
    form_name="editable_task",
    model_class=ProjectTask,
    initial_values=sample_task,
    disabled=False,  # Editable
    spacing="normal",
    metrics_dict={},  # No metrics
)


# Register form routes
good_metrics_form.register_routes(app)
improvement_metrics_form.register_routes(app)
editable_form.register_routes(app)


@rt("/")
def get():
    return fh.Div(
        mui.Container(
            # Header
            mui.Card(
                mui.CardHeader(
                    fh.H1(
                        "📊 Metrics Dictionary Example",
                        cls="text-2xl font-bold text-blue-600",
                    ),
                    fh.P(
                        "Demonstrates how to use metrics_dict to add evaluation scores and comments to form fields.",
                        cls="text-gray-600 mt-2",
                    ),
                ),
                mui.CardBody(
                    mui.Alert(
                        fh.Strong("💡 Key Features:"),
                        fh.Ul(
                            fh.Li(
                                "Color-coded metrics (red/yellow/green based on score)"
                            ),
                            fh.Li("Detailed comments explaining each metric"),
                            fh.Li("Support for nested fields and list items"),
                            fh.Li("Visual indicators for different score ranges"),
                            cls="list-disc list-inside mt-2 space-y-1",
                        ),
                        type="info",
                        cls="mb-4",
                    ),
                ),
            ),
            # Example 1: Good Metrics
            mui.Card(
                mui.CardHeader(
                    fh.H2(
                        "✅ Example 1: High-Quality Metrics",
                        cls="text-xl font-bold text-green-600",
                    ),
                    fh.P(
                        "This form shows mostly positive metrics with high scores and constructive feedback.",
                        cls="text-gray-600 mt-1",
                    ),
                ),
                mui.CardBody(
                    mui.Form(good_metrics_form.render_inputs()),
                ),
                cls="mb-6 border-green-200",
            ),
            # Example 2: Areas for Improvement
            mui.Card(
                mui.CardHeader(
                    fh.H2(
                        "⚠️ Example 2: Areas for Improvement",
                        cls="text-xl font-bold text-yellow-600",
                    ),
                    fh.P(
                        "This form shows lower metrics with specific suggestions for improvement.",
                        cls="text-gray-600 mt-1",
                    ),
                ),
                mui.CardBody(
                    mui.Form(improvement_metrics_form.render_inputs()),
                ),
                cls="mb-6 border-yellow-200",
            ),
            # Example 3: Editable Form (No Metrics)
            mui.Card(
                mui.CardHeader(
                    fh.H2(
                        "✏️ Example 3: Editable Form (No Metrics)",
                        cls="text-xl font-bold text-blue-600",
                    ),
                    fh.P(
                        "Same data model but editable and without metrics for comparison.",
                        cls="text-gray-600 mt-1",
                    ),
                ),
                mui.CardBody(
                    mui.Form(
                        fh.Div(
                            editable_form.render_inputs(),
                            fh.Div(
                                mui.Button(
                                    "💾 Save Changes",
                                    type="submit",
                                    cls=mui.ButtonT.primary,
                                ),
                                editable_form.reset_button("🔄 Reset Form"),
                                cls="mt-4 flex gap-2",
                            ),
                        )
                    ),
                ),
                cls="mb-6 border-blue-200",
            ),
            # Documentation
            mui.Card(
                mui.CardHeader(
                    fh.H2("📖 How to Use Metrics", cls="text-xl font-bold"),
                ),
                mui.CardBody(
                    fh.Div(
                        fh.H3(
                            "Creating MetricEntry Objects:", cls="font-semibold mb-2"
                        ),
                        fh.Pre(
                            """MetricEntry(
    metric=0.85,  # Score from 0.0 to 1.0
    comment="Descriptive feedback about this field"
)""",
                            cls="bg-gray-100 p-3 rounded text-sm mb-4",
                        ),
                        fh.H3("Field Path Examples:", cls="font-semibold mb-2"),
                        fh.Ul(
                            fh.Li(fh.Code('"title"'), " - Top-level field"),
                            fh.Li(fh.Code('"subtasks"'), " - List field overall"),
                            fh.Li(fh.Code('"subtasks[0]"'), " - Specific list item"),
                            fh.Li(fh.Code('"nested.field"'), " - Nested object field"),
                            cls="list-disc list-inside space-y-1 mb-4 text-sm",
                        ),
                        fh.H3("Metric Score Ranges:", cls="font-semibold mb-2"),
                        fh.Ul(
                            fh.Li(
                                fh.Span(
                                    "🔴 0.0 - 0.5:", cls="font-medium text-red-600"
                                ),
                                " Needs significant improvement",
                            ),
                            fh.Li(
                                fh.Span(
                                    "🟡 0.5 - 0.8:", cls="font-medium text-yellow-600"
                                ),
                                " Good with room for improvement",
                            ),
                            fh.Li(
                                fh.Span(
                                    "🟢 0.8 - 1.0:", cls="font-medium text-green-600"
                                ),
                                " Excellent quality",
                            ),
                            cls="list-disc list-inside space-y-1 text-sm",
                        ),
                    ),
                ),
                cls="bg-gray-50",
            ),
        ),
        cls="min-h-screen bg-gray-50 py-8",
    )


if __name__ == "__main__":
    fh.serve()
