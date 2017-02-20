monitのイベントループのコードリーディング
#########################################

:date: 2017-02-20 16:46
:tags: monit, code-reading
:category: blog
:slug: 2017/02/20/monit-event-loop-code-reading

はじめに
--------

`monitのif failed urlのコードリーディング </blog/2017/02/20/monit-if-failed-url-code-reading/>`_ からの続きです。

Event_post関数の実装
--------------------

`src/event.c#L123-L222 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/event.c?at=release-5-11-0&fileviewer=file-view-default#event.c-123:222>`_

.. code-block:: c
        :linenos: table
        :linenostart: 123

        /**
         * Post a new Event
         * @param service The Service the event belongs to
         * @param id The event identification
         * @param state The event state
         * @param action Description of the event action
         * @param s Optional message describing the event
         */
        void Event_post(Service_T service, long id, short state, EventAction_T action, char *s, ...) {
          ASSERT(service);
          ASSERT(action);
          ASSERT(s);
          ASSERT(state == STATE_FAILED || state == STATE_SUCCEEDED || state == STATE_CHANGED || state == STATE_CHANGEDNOT);

          va_list ap;
          va_start(ap, s);
          char *message = Str_vcat(s, ap);
          va_end(ap);

          Event_T e = service->eventlist;
          if (! e) {
            /* Only first failed/changed event can initialize the queue for given event type, thus succeeded events are ignored until first error. */
            if (state == STATE_SUCCEEDED || state == STATE_CHANGEDNOT) {
              DEBUG("'%s' %s\n", service->name, message);
              free(message);
              return;
            }

            /* Initialize event list and add first event. The manadatory informations
             * are cloned so the event is as standalone as possible and may be saved
             * to the queue without the dependency on the original service, thus
             * persistent and managable across monit restarts */
            NEW(e);
            e->id = id;
            gettimeofday(&e->collected, NULL);
            e->source = Str_dup(service->name);
            e->mode = service->mode;
            e->type = service->type;
            e->state = STATE_INIT;
            e->state_map = 1;
            e->action = action;
            e->message = message;
            service->eventlist = e;
          } else {
            /* Try to find the event with the same origin and type identification. Each service and each test have its own custom actions object, so we share actions object address to identify event source. */
            do {
              if (e->action == action && e->id == id) {
                gettimeofday(&e->collected, NULL);

                /* Shift the existing event flags to the left and set the first bit based on actual state */
                e->state_map <<= 1;
                e->state_map |= ((state == STATE_SUCCEEDED || state == STATE_CHANGEDNOT) ? 0 : 1);

                /* Update the message */
                FREE(e->message);
                e->message = message;
                break;
              }
              e = e->next;
            } while (e);

            if (!e) {
              /* Only first failed/changed event can initialize the queue for given event type, thus succeeded events are ignored until first error. */
              if (state == STATE_SUCCEEDED || state == STATE_CHANGEDNOT) {
                DEBUG("'%s' %s\n", service->name, message);
                free(message);
                return;
              }

              /* Event was not found in the pending events list, we will add it.
               * The manadatory informations are cloned so the event is as standalone
               * as possible and may be saved to the queue without the dependency on
               * the original service, thus persistent and managable across monit
               * restarts */
              NEW(e);
              e->id = id;
              gettimeofday(&e->collected, NULL);
              e->source = Str_dup(service->name);
              e->mode = service->mode;
              e->type = service->type;
              e->state = STATE_INIT;
              e->state_map = 1;
              e->action = action;
              e->message = message;
              e->next = service->eventlist;
              service->eventlist = e;
            }
          }

          e->state_changed = Event_check_state(e, state);

          /* In the case that the state changed, update it and reset the counter */
          if (e->state_changed) {
            e->state = state;
            e->count = 1;
          } else
            e->count++;

          handle_event(service, e);
        }


``handle_event`` 関数の実装。
`src/event.c#L605-L655 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/event.c?at=release-5-11-0&fileviewer=file-view-default#event.c-605:655>`_

.. code-block:: c
        :linenos: table
        :linenostart: 605

        /*
         * Handle the event
         * @param E An event
         */
        static void handle_event(Service_T S, Event_T E) {
          ASSERT(E);
          ASSERT(E->action);
          ASSERT(E->action->failed);
          ASSERT(E->action->succeeded);

          /* We will handle only first succeeded event, recurrent succeeded events
           * or insufficient succeeded events during failed service state are
           * ignored. Failed events are handled each time. */
          if (!E->state_changed && (E->state == STATE_SUCCEEDED || E->state == STATE_CHANGEDNOT || ((E->state_map & 0x1) ^ 0x1))) {
            DEBUG("'%s' %s\n", S->name, E->message);
            return;
          }

          if (E->message) {
            /* In the case that the service state is initializing yet and error
             * occured, log it and exit. Succeeded events in init state are not
             * logged. Instance and action events are logged always with priority
             * info. */
            if (E->state != STATE_INIT || E->state_map & 0x1) {
              if (E->state == STATE_SUCCEEDED || E->state == STATE_CHANGEDNOT || E->id == Event_Instance || E->id == Event_Action)
                LogInfo("'%s' %s\n", S->name, E->message);
              else
                LogError("'%s' %s\n", S->name, E->message);
            }
            if (E->state == STATE_INIT)
              return;
          }

          if (E->state == STATE_FAILED || E->state == STATE_CHANGED) {
            if (E->id != Event_Instance && E->id != Event_Action) { // We are not interested in setting error flag for instance and action events
              S->error |= E->id;
              /* The error hint provides second dimension for error bitmap and differentiates between failed/changed event states (failed=0, chaged=1) */
              if (E->state == STATE_CHANGED)
                S->error_hint |= E->id;
              else
                S->error_hint &= ~E->id;
            }
            handle_action(E, E->action->failed);
          } else {
            S->error &= ~E->id;
            handle_action(E, E->action->succeeded);
          }

          /* Possible event state change was handled so we will reset the flag. */
          E->state_changed = FALSE;
        }
