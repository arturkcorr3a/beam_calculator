from indeterminatebeam import Support

class PillarSupport(Support):
    """Class representing a pillar support."""
    
    def __init__(self, position: float, support_type: str):
        """
        Initialize a beam support.
        
        Args:
            position: Position along the beam length (m)
            support_type: Type of support ('fixed', 'pinned', 'roller')
        """
        super().__init__(position, support_type)
        # TODO set beam-pillar coherence
        # FIXME define type and calculate spring constant