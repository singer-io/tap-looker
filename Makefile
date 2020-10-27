.DEFAULT_GOAL := test

lint:
	pylint tap_looker --disable missing-module-docstring,superfluous-parens,missing-module-docstring,missing-function-docstring,line-too-long,duplicate-key,protected-access,too-many-arguments,too-many-locals,too-many-nested-blocks,too-many-statements,trailing-whitespace,unused-variable,inconsistent-return-statements,duplicate-code,invalid-name,too-many-branches,missing-class-docstring,no-else-raise,no-else-return
