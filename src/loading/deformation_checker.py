class DeformationChecker:
    """
    Excessive deformation verification for linear elements, according to ELS (Service Limit State) criteria, based on ABNT NBR 8681 - Section 7.3.2.

    For slabs (superficial elements), ABNT NBR 6118 - Section 19.3.1, redirects to the linear elements verification
    """

    def verify(self) -> bool:
        """
        Verifies if the deformation of the element is within acceptable limits.

        :return: True if the deformation is acceptable, False otherwise
        :rtype: bool
        """
        # IMPLEMENT
        return True