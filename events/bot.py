from datetime import date
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Attendance, Event, Message, Registration


def get_or_create_bot_user():
  """Ensures a dedicated bot user account exists in the database."""
  bot_user, _ = User.objects.get_or_create(
      username='EventBot',
      defaults={
          'first_name': 'Event',
          'last_name': 'Bot (Assistant)',
          'is_staff': False,
          'is_superuser': False,
      },
  )
  return bot_user


def generate_bot_response(user, user_text):
  """Analyzes the user's input and generates intelligent dynamic replies."""
  text = user_text.lower().strip()
  today = date.today()

  # 1. Greetings
  if any(w in text for w in ['hi', 'hello', 'hey', 'start', 'greetings']):
    return (
        f'Hello {user.first_name or user.username}! 👋 I am your Event'
        ' Assistant.\n\n'
        'You can ask me things like:\n'
        '• "Show upcoming events"\n'
        '• "What are my registered events?"\n'
        '• "Check status of [event name]"\n'
        '• "Event categories"\n'
        '• "Help" for more commands'
    )

  # 2. Upcoming Events
  elif 'upcoming' in text:
    events = Event.objects.filter(
        event_date__gte=today, status='Upcoming'
    ).order_by('event_date')[:4]
    if events.exists():
      reply = '📅 **Upcoming Events:**\n'
      for ev in events:
        category_name = ev.category.name if ev.category else 'General'
        reply += (
            f'• **{ev.name}** ({category_name}) on'
            f" {ev.event_date.strftime('%b %d, %Y')} at {ev.venue}\n"
        )
      return (
          reply
          + "\nYou can register for any of these under 'Register for Event'!"
      )
    return 'There are currently no upcoming events scheduled.'

  # 3. User's Own Registrations
  elif (
      'my registration' in text
      or 'registered' in text
      or 'my events' in text
      or 'enrolled' in text
  ):
    conditions = Q()
    if user.email:
      conditions |= Q(email__iexact=user.email)
    if user.username:
      conditions |= Q(full_name__iexact=user.username)
    full_name = user.get_full_name().strip()
    if full_name:
      conditions |= Q(full_name__iexact=full_name)

    regs = Registration.objects.filter(conditions).select_related('event')
    if regs.exists():
      reply = '🎟️ **Your Registered Events:**\n'
      for r in regs:
        status = 'Completed' if r.event.event_date < today else 'Upcoming'
        reply += f"• **{r.event.name}** — Date: {r.event.event_date.strftime('%b %d, %Y')} [{status}]\n"
      return reply
    return "You have not registered for any events yet. Check out the 'Event List' to get started!"

  # 4. Specific Event Lookup
  elif (
      'event' in text
      or 'venue' in text
      or 'date' in text
      or 'time' in text
      or 'status' in text
  ):
    # Try searching matching event names
    for word in text.split():
      if len(word) > 2 and word not in [
          'what',
          'when',
          'where',
          'show',
          'tell',
          'event',
          'the',
          'for',
          'about',
      ]:
        match = Event.objects.filter(name__icontains=word).first()
        if match:
          status_str = (
              'Completed' if match.event_date < today else match.status
          )
          return (
              f'📌 **Event Details: {match.name}**\n'
              f"• Category: {match.category.name if match.category else 'General'}\n"
              f"• Date: {match.event_date.strftime('%b %d, %Y')}\n"
              f"• Venue: {match.venue}\n"
              f"• Status: {status_str}\n"
              f"• Description: {match.description or 'No description available.'}"
          )

  # 5. Help Menu
  elif 'help' in text or 'menu' in text:
    return (
        '🤖 **Here is how I can assist you:**\n'
        '1. Type **"upcoming"** to see live upcoming events.\n'
        '2. Type **"my registrations"** to view your booked tickets/events.\n'
        '3. Type the **name of any event** (e.g. "codefest") to get full venue and schedule details.\n'
        '4. For administrative queries, please contact event organizers directly.'
    )

  # Default fallback
  return (
      "I'm sorry, I didn't quite catch that. 🤔\nType **help** or **upcoming"
      ' events** to see what I can answer for you!'
  )