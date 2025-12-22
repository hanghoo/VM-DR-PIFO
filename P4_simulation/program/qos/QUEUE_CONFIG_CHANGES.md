# Queue Processing Configuration Changes for Minimal Topology

## Summary

When reducing from **72 flows** to **8 flows**, the following scheduler configurations need to be updated:

---

## Required Changes ✅ COMPLETED

### 1. DRR Scheduler (`user_externs_DRR/`) ✅

**File: `DRR.cpp`**
- ✅ **Line 30**: Changed `number_of_pkts_per_queue_each_level = {72}` → `{8}`
- ✅ **Line 72**: Changed `quota_each_queue` from 72 entries to 8 entries

**File: `DRR.h`**
- ✅ **Line 233**: Changed `for (int i = 0; i<72 ;i++)` → `for (int i = 0; i<8 ;i++)`
- ✅ **Line 278**: Changed `for (int i = 0; i<72 ;i++)` → `for (int i = 0; i<8 ;i++)`

### 2. DR-PIFO Scheduler (`user_externs_dr_pifo/`) ✅

**File: `DR_PIFO.cpp`**
- ✅ **Line 14**: Changed `number_of_pkts_per_queue_each_level = {80}` → `{8}`

### 3. pFabric Scheduler (`user_externs_pFabric/`) ✅

**File: `pFabric.cpp`**
- ✅ **Line 15**: Changed `number_of_pkts_per_queue_each_level = {80}` → `{8}`

### 3. BMv2 Files Folder (`BMv2 files/`) ✅

**These files are used by the behavioral-model during compilation:**

- ✅ **TM_buffer_DRR.h**: Updated `number_of_pkts_per_queue_each_level = {72}` → `{8}` and `quota_each_queue` from 72 to 8 entries
- ✅ **TM_buffer_dr_pifo.h**: Updated `number_of_pkts_per_queue_each_level = {80}` → `{8}`
- ✅ **TM_buffer_pFabric.h**: Updated `number_of_pkts_per_queue_each_level = {80}` → `{8}`
- ✅ **TM_buffer_pieo.h**: Updated `number_of_pkts_per_queue_each_level = {80}` → `{8}`
- ✅ **TM_buffer_WDRR.h**: Updated `number_of_pkts_per_queue_each_level = {72}` → `{8}` and both `quota_each_queue` and `quantums` from 72 to 8 entries
- ✅ **TM_buffer_WRR.h**: Updated `number_of_pkts_per_queue_each_level = {72}` → `{8}` and both `quota_each_queue` and `quantums` from 72 to 8 entries

### 4. Other Schedulers

Other scheduler implementations (RL_SP_NWC, etc.) may have similar hardcoded values if you plan to use them.

---

## Impact

### Memory Usage
- **Before**: Allocates space for 72 flows
- **After**: Allocates space for 8 flows
- **Savings**: ~89% reduction in memory usage

### Performance
- Smaller arrays = faster iteration in loops
- Less memory allocation = better cache performance

### Functionality
- **Critical**: The loops that iterate 72 times must be changed to 8, otherwise:
  - Quota initialization will fail
  - Dequeue operations may access invalid indices
  - Flow tracking will be incorrect

---

## Recommendation

**Option 1: Create Minimal Versions** (Recommended)
- Create separate minimal versions of scheduler files
- Keep original versions for full topology
- Switch between them based on topology

**Option 2: Use Configuration Parameters**
- Make the flow count configurable via compile-time defines
- Use `#ifdef MINIMAL_TOPOLOGY` to switch values

**Option 3: Direct Modification**
- Update the files directly if you only plan to use minimal topology

---

## Testing Checklist

After making changes, verify:
- [ ] Scheduler compiles without errors
- [ ] All 8 flows are properly tracked
- [ ] Quota initialization works for all 8 flows
- [ ] Dequeue operations process all flows correctly
- [ ] No array out-of-bounds errors
- [ ] Memory usage is reduced

