import asyncio
import functools
import logging
import yaml

from .actions import ACTIONS
from .selectors import SELECTORS
from .plan import generate_plan, validate_plan


log = logging.getLogger("glitch")
DEFAULT_PLAN_NAME = "glitch_plan.yaml"


def default_resolver(model, kind, name):
    if kind not in ["application", "unit", "model", "controller", "relation"]:
        return None
    entities = getattr(model, kind + "s")
    obj = entities[name]
    return obj


def select(model, selectors, objects=None, resolver=default_resolver):
    if not selectors:
        if objects is None:
            # TODO: custom Exception class
            raise ValueError('No valid objects specified by selectors')
        return objects

    # if there are string names being passed (from a serialized plan for
    # example) we must resolve them relative to the current model. This is
    # pluggable using a resolver object which takes a model,
    working_set = None
    args = [model]
    # This can raise many an exception
    for selector in selectors:
        selector = selector.copy()
        select_func = SELECTORS.get(selector.pop('selector'))
        for k, v in selector.items():
            if isinstance(v, str):
                # attempt resolution
                o = resolver(model, k, v)
                if o is not None:
                    selector[k] = o

            working_set = select_func(*args, **selector)
            args = [model, working_set]
    return working_set


async def glitch(context, rule, action, event=None):
    """
    Perform a set of actions against a model, with a mind toward causing
    trouble.

    The set of actions is defined by a plan, which is either passed in at
    config time, or generated on the fly.

    We write the last plan to be run out to a YAML file.

    """
    rule.log.info("Starting glitch")

    output_filename = DEFAULT_PLAN_NAME
    model = context.model

    glitch_plan = validate_plan(
        action.args.get('glitch_plan') or generate_plan(
            model,
            num=action.args.get('glitch_num', 5)))

    rule.log.info("Writing glitch plan to {}".format(output_filename))
    with open(output_filename, 'w') as output_file:
        output_file.write(yaml.dump(glitch_plan))

    # Execute glitch plan. We perform destructive operations here!
    for action in glitch_plan['actions']:
        actionf = ACTIONS[action.pop('action')]
        selectors = action.pop('selectors')
        # Find a set of units to act upon
        objects = select(model, selectors)

        # Run the specified action on those units
        rule.log.debug("GLITCHING {}: {}".format(actionf.__name__, action))
        context.bus.dispatch(
            origin="glitch",
            payload=functools.partial(actionf, model, objects, **action),
            kind="glitch.activate"
        )
        await asyncio.sleep(2, loop=context.loop)

    rule.log.info("Finished glitch")
    return True
