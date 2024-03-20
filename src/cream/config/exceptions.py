class InvalidChainNameError(ValueError):
	"""Exception raised when an invalid chain name is provided."""
	def __init__(self, chain_name, message="Invalid chain name provided"):
		self.chain_name = chain_name
		self.message = f"{message}: {chain_name}"
		super().__init__(self.message)