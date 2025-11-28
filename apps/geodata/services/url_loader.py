class URLLayerLoader:
	"""
	Loader for URL-based layers.
	"""
	
	def __init__(self, url: str):
		self.url = url
	
	def load(self):
		"""
		Load layer from URL.
		"""
		raise NotImplementedError("Subclasses must implement load method")
