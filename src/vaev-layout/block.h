#pragma once

#include "base.h"

namespace Vaev::Layout {

Output blockLayout(Tree &t, Frag &f, Input input);

Px blockMeasure(Tree &t, Frag &f, Axis axis, IntrinsicSize intrinsic, Px availableSpace);

} // namespace Vaev::Layout
