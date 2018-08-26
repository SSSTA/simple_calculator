import math

dot_tokens = ["."]
bracket_tokens = ["(", ")"]
second_priority_tokens = ["*", "/"]
third_priority_tokens = ["+", "-"]

op_map = {
    "+": '__add__',
    "-": '__sub__',
    "*": '__mul__',
    "/": '__truediv__'
}


class TokenType(object):
    DOT = 1
    SIGN = 2
    NUMBER = 3
    BRACKET = 4
    SECOND_PRIORITY_OP = 5
    THIRD_PRIORITY_OP = 6
    CONSTANT_OR_FUNCTION_NAME = 7


class Token(object):
    def __init__(self, token_str, token_type):
        self.token_str = token_str
        self.token_type = token_type
        self.type_annotation = {v: k for k, v in TokenType.__dict__.items()}

    @property
    def is_left_bracket(self) -> bool:
        return self.token_str == "("

    @property
    def is_right_bracket(self) -> bool:
        return self.token_str == ")"

    def __repr__(self):
        return "<Token object (Type={}, Value='{}')>".format(self.type_annotation[self.token_type], self.token_str)


class ExpressionLexer(object):
    def __init__(self, string: str):
        self.string = string

    def lex(self):
        result = []
        current_pos = 0
        current_type = 0
        current_str = ""

        def push():
            nonlocal current_type, current_str
            if current_type > 0:
                result.append(Token(current_str, current_type))
            current_type = 0
            current_str = ""

        while current_pos < len(self.string):
            v = self.string[current_pos]
            current_pos += 1
            if v.isnumeric() or v in dot_tokens:
                if current_type == TokenType.NUMBER:
                    current_str += v
                else:
                    push()
                    current_str = v
                    current_type = TokenType.NUMBER
                continue

            if v.isalpha():
                if current_type == TokenType.CONSTANT_OR_FUNCTION_NAME:
                    current_str += v
                else:
                    push()
                    current_str = v
                    current_type = TokenType.CONSTANT_OR_FUNCTION_NAME
                continue

            if v in third_priority_tokens:
                push()
                if not result or result[-1].token_type in [TokenType.SECOND_PRIORITY_OP, TokenType.THIRD_PRIORITY_OP]:
                    current_type = TokenType.SIGN
                else:
                    current_type = TokenType.THIRD_PRIORITY_OP
                current_str = v
                push()
                continue

            if v in second_priority_tokens:
                push()
                current_str = v
                current_type = TokenType.SECOND_PRIORITY_OP
                push()
                continue

            if v in bracket_tokens:
                push()
                current_str = v
                current_type = TokenType.BRACKET
                push()
                continue

        push()
        return result


class BaseExpression(object):
    def eval(self):
        raise NotImplementedError


class NumberExpression(BaseExpression):
    def __init__(self, value):
        self.value = value

    def eval(self):
        return float(self.value)


class BinaryExpression(BaseExpression):
    def __init__(self, expr1, op, expr2):
        self.expr1 = expr1
        self.op = op
        self.expr2 = expr2

    def eval(self):
        return getattr(self.expr1.eval(), op_map[self.op])(self.expr2.eval())


class ConstantExpression(BaseExpression):
    def __init__(self, name):
        self.name = name

    def eval(self):
        return getattr(math, self.name)


class FunctionExpression(BaseExpression):
    def __init__(self, func_name, expr):
        self.func_name = func_name
        self.expr = expr

    def eval(self):
        return getattr(math, self.func_name)(self.expr.eval())


class ExpressionParser(object):
    def __init__(self, token_list: list):
        self.token_list = token_list

    def parse_sign(self, pos: int) -> (BaseExpression, int):
        current_token: Token = self.token_list[pos]
        result, length = self.parse_first_priority(pos + 1)
        return BinaryExpression(NumberExpression("0"), current_token.token_str, result), length + 1

    def parse_number(self, pos: int) -> (BaseExpression, int):
        current_token: Token = self.token_list[pos]
        return NumberExpression(current_token.token_str), 1

    def parse_bracket(self, pos: int) -> (BaseExpression, int):
        current_token: Token = self.token_list[pos]
        assert current_token.token_type == TokenType.BRACKET
        expr, length = self.parse_expr(pos + 1)
        assert current_token.token_type == TokenType.BRACKET
        return expr, length + 2

    def parse_constant_or_function(self, pos: int) -> (BaseExpression, int):
        current_token: Token = self.token_list[pos]
        fn = current_token.token_str
        if pos + 1 == len(self.token_list):
            return ConstantExpression(fn), 1

        current_token: Token = self.token_list[pos + 1]
        if current_token.is_left_bracket:
            expr, length = self.parse_bracket(pos + 1)
            return FunctionExpression(fn, expr), 1 + length
        else:
            return ConstantExpression(fn), 1

    def parse_first_priority(self, pos: int) -> (BaseExpression, int):
        current_token: Token = self.token_list[pos]
        if current_token.token_type == TokenType.BRACKET:
            return self.parse_bracket(pos)
        elif current_token.token_type in [TokenType.DOT, TokenType.NUMBER]:
            return self.parse_number(pos)
        elif current_token.token_type == TokenType.CONSTANT_OR_FUNCTION_NAME:
            return self.parse_constant_or_function(pos)
        elif current_token.token_type == TokenType.SIGN:
            return self.parse_sign(pos)
        else:
            raise ValueError("expression begin with binary op")

    def parse_second_priority(self, pos: int, left_expr: BaseExpression) -> (BaseExpression, int):
        current_token: Token = self.token_list[pos]
        right_expr, length = self.parse_first_priority(pos + 1)
        return BinaryExpression(left_expr, current_token.token_str, right_expr), length + 1

    def parse_third_priority(self, pos: int, left_expr: BaseExpression) -> (BaseExpression, int):
        third_priority_op_token: Token = self.token_list[pos]

        current_expr, length = self.parse_first_priority(pos + 1)
        current_length = length

        while pos + current_length + 1 < len(self.token_list):
            current_token = self.token_list[current_length + pos + 1]
            if current_token.token_type == TokenType.SECOND_PRIORITY_OP:
                current_expr, length = self.parse_second_priority(current_length + pos + 1, current_expr)
                current_length += length
            else:
                break

        return BinaryExpression(left_expr, third_priority_op_token.token_str, current_expr), current_length + 1

    def parse_expr(self, pos: int) -> (BaseExpression, int):
        current_expr, length = self.parse_first_priority(pos)
        current_length = length
        while pos + current_length < len(self.token_list):
            current_token = self.token_list[current_length + pos]
            if current_token.token_type == TokenType.THIRD_PRIORITY_OP:
                current_expr, length = self.parse_third_priority(current_length + pos, current_expr)
                current_length += length
            elif current_token.token_type == TokenType.SECOND_PRIORITY_OP:
                current_expr, length = self.parse_second_priority(current_length + pos, current_expr)
                current_length += length
            else:
                break

        return current_expr, current_length


e, _ = ExpressionParser(ExpressionLexer("-sin(pi/2)+12+13+6*-(4+log(e))").lex()).parse_expr(0)
print(e.eval())
