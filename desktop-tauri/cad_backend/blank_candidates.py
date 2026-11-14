"""Conservative stock alternatives; envelope is not a manufacturing proof."""
import math

def envelope_candidate(dimensions, finished_volume):
    if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 3:
        return None
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in dimensions):
        return None
    if type(finished_volume) not in (int, float) or not math.isfinite(finished_volume) or finished_volume <= 0:
        return None
    dims=sorted(dimensions, reverse=True)
    volume=math.prod(dims)
    if not math.isfinite(volume) or volume <= 0 or finished_volume > volume * 1.000001:
        return None
    return {'kind':'rectangular-blank-candidate','dimensionsMm':dims,
            'volumeMm3':volume,'removedVolumeMm3':max(0,volume-finished_volume),
            'utilization':min(1,finished_volume/volume),
            'confidence':'envelope-only','requiresReview':True,
            'source':'measured enclosing dimensions of finished B-Rep',
            'limitations':'Possible solid blank only; may be unsuitable for assemblies, castings, purchased parts or deposited weld metal. No grade, catalogue size or operation is certified.'}
