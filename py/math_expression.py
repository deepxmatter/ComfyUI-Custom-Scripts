import ast
import math
import random
import operator as op

operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Pow: op.pow,
    ast.BitXor: op.xor,
    ast.USub: op.neg,
    ast.Mod: op.mod
}

# TODO: restructure args to provide more info, generate hint based on args to save duplication
functions = {
    "round": {
        "args": (1, 2),
        "call": lambda a, b = None: round(a, b),
        "hint": "number, dp? = 0"
    },
    "ceil": {
        "args": (1, 1),
        "call": lambda a: math.ceil(a),
        "hint": "number"
    },
    "floor": {
        "args": (1, 1),
        "call": lambda a: math.floor(a),
        "hint": "number"
    },
    "min": {
        "args": (2, None),
        "call": lambda *args: min(*args),
        "hint": "...numbers"
    },
    "max": {
        "args": (2, None),
        "call": lambda *args: max(*args),
        "hint": "...numbers"
    },
    "randomint": {
        "args": (2, 2),
        "call": lambda a, b: random.randint(a, b),
        "hint": "min, max"
    },
    "randomchoice": {
        "args": (2, None),
        "call": lambda *args: random.choice(args),
        "hint": "...numbers"
    },
}

autocompleteWords = list({
    "text": x,
    "value": f"{x}()",
    "showValue": False,
    "hint": f"{functions[x]['hint']}",
    "caretOffset": -1
} for x in functions.keys())


class MathExpression:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "expression": ("STRING", {"multiline": True, "dynamicPrompts": False, "pysssss.autocomplete": {
                    "words": autocompleteWords,
                    "separator": ""
                }}),
            },
            "optional": {
                "a": ("INT,FLOAT,IMAGE,LATENT", ),
                "b": ("INT,FLOAT,IMAGE,LATENT",),
                "c": ("INT,FLOAT,IMAGE,LATENT", ),
            },
            "hidden": {"extra_pnginfo": "EXTRA_PNGINFO",
                       "prompt": "PROMPT"},
        }

    RETURN_TYPES = ("INT", "FLOAT", )
    FUNCTION = "evaluate"
    CATEGORY = "utils"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(s, expression, **kwargs):
        if "random" in expression:
            return float("nan")
        return expression

    def get_widget_value(self, extra_pnginfo, prompt, node_name, widget_name):
        workflow = extra_pnginfo["workflow"] if "workflow" in extra_pnginfo else { "nodes": [] }
        node_id = None
        for node in workflow["nodes"]:
            name = node["type"]
            if "properties" in node:
                if "Node name for S&R" in node["properties"]:
                    name = node["properties"]["Node name for S&R"]
            if name == node_name:
                node_id = node["id"]
                break
            if "title" in node:
                name = node["title"]
            if name == node_name:
                node_id = node["id"]
                break
        if node_id is not None:
            values = prompt[str(node_id)]
            if "inputs" in values:
                if widget_name in values["inputs"]:
                    return values["inputs"][widget_name]
            raise NameError(f"Widget not found: {node_name}.{widget_name}")
        raise NameError(f"Node not found: {node_name}.{widget_name}")

    def get_size(self, target, property):
        if isinstance(target, dict) and "samples" in target:
            # Latent
            if property == "width":
                return target["samples"].shape[3] * 8
            return target["samples"].shape[2] * 8
        else:
            # Image
            if property == "width":
                return target.shape[2]
            return target.shape[1]

    def evaluate(self, expression, prompt, extra_pnginfo={}, a=None, b=None, c=None):
        expression = expression.replace('\n', ' ').replace('\r', '')
        node = ast.parse(expression, mode='eval').body

        lookup = {"a": a, "b": b, "c": c}

        def eval_expr(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                return operators[type(node.op)](float(eval_expr(node.left)), float(eval_expr(node.right)))
            elif isinstance(node, ast.UnaryOp):
                return operators[type(node.op)](eval_expr(node.operand))
            elif isinstance(node, ast.Attribute):
                if node.value.id in lookup:
                    if node.attr == "width" or node.attr == "height":
                        return self.get_size(lookup[node.value.id], node.attr)

                return self.get_widget_value(extra_pnginfo, prompt, node.value.id, node.attr)
            elif isinstance(node, ast.Name):
                if node.id in lookup:
                    val = lookup[node.id]
                    if isinstance(val, (int, float, complex)):
                        return val
                    else:
                        raise TypeError(
                            f"Compex types (LATENT/IMAGE) need to reference their width/height, e.g. {node.id}.width")
                raise NameError(f"Name not found: {node.id}")
            elif isinstance(node, ast.Call):
                if node.func.id in functions:
                    fn = functions[node.func.id]
                    l = len(node.args)
                    if l < fn["args"][0] or (fn["args"][1] is not None and l > fn["args"][1]):
                        if fn["args"][1] is None:
                            toErr = " or more"
                        else:
                            toErr = f" to {fn['args'][1]}"
                        raise SyntaxError(
                            f"Invalid function call: {node.func.id} requires {fn['args'][0]}{toErr} arguments")
                    args = []
                    for arg in node.args:
                        args.append(eval_expr(arg))
                    return fn["call"](*args)
                raise NameError(f"Invalid function call: {node.func.id}")
            else:
                raise TypeError(node)

        r = eval_expr(node)
        return {"ui": {"value": [r]}, "result": (int(r), float(r),)}


NODE_CLASS_MAPPINGS = {
    "MathExpression|pysssss": MathExpression,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MathExpression|pysssss": "Math Expression 🐍",
}
