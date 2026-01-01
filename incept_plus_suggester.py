"""
Incept+ Suggestion Generator
Uses Claude API to generate intelligent improvement suggestions for projects.
"""

import os
import json
import anthropic
from datetime import datetime
import config
import database


def generate_suggestions(project_id, direction, context=None, max_suggestions=10):
    """
    Generate improvement suggestions for a project based on the given direction.

    Args:
        project_id: ID of the project to generate suggestions for
        direction: Description of what improvements to focus on
        context: Optional additional context about the codebase
        max_suggestions: Maximum number of suggestions to generate

    Returns:
        List of suggestion dictionaries with title, description, implementation_details, etc.
    """
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    # Get project info
    project = database.get_project(project_id)
    if not project:
        raise ValueError(f"Project ID {project_id} not found")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # Get settings for this project
    settings = database.get_incept_plus_settings(project_id)
    model = settings.get('suggestion_model', 'claude-sonnet-4-20250514')

    # Build system prompt
    system_prompt = """You are an expert software architect and developer. Your task is to analyze a codebase and suggest concrete, actionable improvements.

For each suggestion, provide:
1. A clear, concise title (5-10 words)
2. A detailed description explaining why this improvement is valuable
3. Specific implementation details including:
   - Which files need to be modified or created
   - Key code changes required
   - Any dependencies or prerequisites
4. Category (feature, bugfix, performance, refactoring, ui, testing, documentation, security)
5. Priority (1=critical, 2=high, 3=medium, 4=low, 5=nice-to-have)
6. Estimated effort (small, medium, large)
7. Dependencies on other changes

Be specific and practical. Focus on improvements that add real value.
Return your response as a JSON array of suggestions."""

    # Build user prompt
    user_prompt = f"""I'm working on a project called "{project['name']}". Here's what I want to improve:

Direction: {direction}

"""

    if project.get('description'):
        user_prompt += f"""Project Description:
{project['description']}

"""

    if project.get('project_type'):
        user_prompt += f"""Project Type: {project['project_type']}

"""

    if context:
        user_prompt += f"""Additional Context:
{context}

"""

    user_prompt += f"""Please suggest {max_suggestions} specific improvements that align with this direction.

Return a JSON array with this structure:
[
  {{
    "title": "Short descriptive title",
    "description": "Detailed explanation of the improvement and its value",
    "implementation_details": "Step-by-step implementation guide with specific file paths and code changes",
    "category": "feature|bugfix|performance|refactoring|ui|testing|documentation|security",
    "priority": 1-5,
    "estimated_effort": "small|medium|large",
    "dependencies": "Any prerequisites or related changes needed, or null"
  }}
]"""

    try:
        # Call Claude API
        response = client.messages.create(
            model=model,
            max_tokens=8000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        # Extract suggestions from response
        content = response.content[0].text

        # Try to parse JSON from the response
        # Sometimes Claude wraps JSON in markdown code blocks
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            content = content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.find("```", json_start)
            content = content[json_start:json_end].strip()

        suggestions = json.loads(content)

        # Validate and normalize suggestions
        normalized_suggestions = []
        for i, sug in enumerate(suggestions[:max_suggestions]):
            normalized_suggestions.append({
                'title': sug.get('title', f'Improvement #{i+1}'),
                'description': sug.get('description', ''),
                'implementation_details': sug.get('implementation_details', ''),
                'category': sug.get('category', 'feature'),
                'priority': int(sug.get('priority', 3)),
                'estimated_effort': sug.get('estimated_effort', 'medium'),
                'dependencies': sug.get('dependencies'),
                'context': direction
            })

        return normalized_suggestions

    except json.JSONDecodeError as e:
        # If JSON parsing fails, return a fallback suggestion with the raw response
        return [{
            'title': 'Claude Response (Parse Error)',
            'description': f'Failed to parse suggestions. Raw response: {content[:500]}...',
            'implementation_details': 'Manual review required',
            'category': 'feature',
            'priority': 3,
            'estimated_effort': 'unknown',
            'dependencies': None,
            'context': direction
        }]
    except Exception as e:
        raise Exception(f"Failed to generate suggestions: {str(e)}")


def save_suggestions_to_db(project_id, suggestions):
    """Save generated suggestions to the database."""
    suggestion_ids = []
    for sug in suggestions:
        suggestion_id = database.add_incept_suggestion(
            project_id=project_id,
            title=sug['title'],
            description=sug['description'],
            implementation_details=sug['implementation_details'],
            category=sug.get('category', 'feature'),
            priority=sug.get('priority', 3),
            context=sug.get('context'),
            estimated_effort=sug.get('estimated_effort'),
            dependencies=sug.get('dependencies')
        )
        suggestion_ids.append(suggestion_id)
    return suggestion_ids


def generate_and_save_suggestions(project_id, direction, context=None, max_suggestions=10):
    """Generate suggestions and save them to the database."""
    suggestions = generate_suggestions(project_id, direction, context, max_suggestions)
    suggestion_ids = save_suggestions_to_db(project_id, suggestions)

    # Pair IDs with suggestions
    for i, suggestion_id in enumerate(suggestion_ids):
        if i < len(suggestions):
            suggestions[i]['id'] = suggestion_id

    return suggestions
