
//////////////////////////////////////////////////// todo list
//////////////////////////////////////////////////// 1) force dequeue and error correction are not unsigned short introduced properly yet.
//////////////////////////////////////////////////// 2) add the arrival time in each packet (I am using the pkt_ptr instead in the enqueue_FS now)

#ifndef SIMPLE_SWITCH_PSA_DIV_H_
#define SIMPLE_SWITCH_PSA_DIV_H_
#include <bm/bm_sim/logger.h>
#include <bm/bm_sim/extern.h>
#define _STDC_WANT_LIB_EXT1_ 1
#define _CRT_SECURE_NO_WARNINGS
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <chrono>
#include <iostream>
#include <map>
#include <mutex>
#include <numeric>
#include <queue>
#include <vector>
#include <ctime>
using namespace std::chrono;
#pragma once

// ========== LOGGING CONTROL ==========
// Performance mode: Set to 1 to COMPLETELY disable all logging (zero overhead)
// This removes all log calls at compile time, ensuring accurate latency measurements
// Set to 0 to enable logging (for debugging)
#ifndef WRR_DISABLE_LOGGING
//#define WRR_DISABLE_LOGGING 0  // Default: enable logging
#define WRR_DISABLE_LOGGING 1
#endif

// Verbose logging control: Set to 1 to enable verbose debug logs
// Set to 0 to disable verbose logging (faster, smaller logs)
#ifndef WRR_VERBOSE_LOGGING
#define WRR_VERBOSE_LOGGING 0
#endif

// Macro for conditional verbose logging
#if WRR_VERBOSE_LOGGING
#define WRR_LOG_VERBOSE(level, ...) bm::Logger::get()->level(__VA_ARGS__)
#else
#define WRR_LOG_VERBOSE(level, ...) ((void)0)
#endif

// Macro for all logging (completely disabled in performance mode)
#if WRR_DISABLE_LOGGING
#define WRR_LOG(level, ...) ((void)0)
#define WRR_LOG_INFO(...) ((void)0)
#define WRR_LOG_DEBUG(...) ((void)0)
#define WRR_LOG_WARN(...) ((void)0)
#define WRR_LOG_ERROR(...) ((void)0)
#else
#define WRR_LOG(level, ...) bm::Logger::get()->level(__VA_ARGS__)
#define WRR_LOG_INFO(...) bm::Logger::get()->info(__VA_ARGS__)
#define WRR_LOG_DEBUG(...) bm::Logger::get()->debug(__VA_ARGS__)
#define WRR_LOG_WARN(...) bm::Logger::get()->warn(__VA_ARGS__)
#define WRR_LOG_ERROR(...) bm::Logger::get()->error(__VA_ARGS__)
#endif
// ======================================

namespace bm {

// if the rank = 0, that means this level is not used (pkts will be handled in a FIFO order in this level), the lowest rank in any level is "1".

// this is the main class of the AR-PIFO scheduler that will be used later in any usage of the scheduler.
class hier_scheduler : public bm::ExternType {
 public:
  BM_EXTERN_ATTRIBUTES {
    BM_EXTERN_ATTRIBUTE_ADD(verbose);
  }


void init() override {  // Attributes
  static constexpr std::uint32_t QUIET = 0u;
  // Init variables
  verbose_ = verbose.get<std::uint32_t>() != QUIET;
  // ========== DEBUG: Verify module loaded ==========
  WRR_LOG_INFO("========================================");
  WRR_LOG_INFO("WRR Module INITIALIZED successfully!");
  WRR_LOG_INFO("========================================");
  // =================================================
};

// the packet struct that presents any packet inside the scheduler.
	struct packet {
		unsigned int level3_flow_id;
		unsigned int flow_id;
		unsigned int rank;
		unsigned int pred;
		unsigned int pkt_ptr;
		std::vector<unsigned int> levels_ranks;
		unsigned int arrival_time;
	};
// The flow scheduler struct : which is a queue that sorts 1 head packet from each flow.
	struct flow_scheduler {
		std::shared_ptr<packet> object;
		std::shared_ptr<flow_scheduler> next;
	};
// The Fifo bank struct : which consists of multiple FIFO queues, each one is dedicated to one flow, and stores all packets from this flow except the head packet.
	struct fifo_bank {
		unsigned int flow_id;
		std::shared_ptr<packet> object;
		std::shared_ptr<fifo_bank> bottom;
		std::shared_ptr<fifo_bank> left;
	};

	static unsigned int time_now; // the current time, increment by 1 each time we call the scheduler for a dequeue (which is continous)

// level 3 of the hierarchy variables
	static std::vector<unsigned int> number_of_queues_per_level;
	static std::vector<unsigned int> number_of_pkts_per_queue_each_level;
	static std::vector<unsigned int> error_detected_each_level;
	static std::vector<unsigned int> internal_force_flow_id_each_level;

	static std::vector<std::shared_ptr<flow_scheduler>> FS;

	static std::vector<std::shared_ptr<fifo_bank>> FB; // the fifo bank queues, each flow scheduler has its own FIFO bank which stores the rest of packets of the flow handled in this flow scheduler.

	static std::vector<unsigned int> new_ranks_each_level;
// level 2 of the hierarchy variables

// level 1 of the hierarchy variables (root)


	std::shared_ptr<packet> deq_packet_ptr = NULL; // the pointer to the dequeued packet
	static unsigned int number_of_enqueue_packets; // the total number of enqueued packets until now.

	static unsigned int number_of_read_packets; // the total number of captured packets by the TM_buffer.h until now.

	static unsigned int number_of_dequeue_packets; // the total number of dequeued packets until now.

	static unsigned int switch_is_ready;

	static unsigned int number_levels;

// these variables will contain the inputs that will be inserted by the user, to be used later.
	unsigned int flow_id;
	//std::vector<unsigned int> pkt_levels_ranks = std::vector<unsigned int>(number_levels);
	static std::vector<unsigned int> pkt_levels_ranks;

	std::vector<unsigned int> enq_flow_id_each_level = std::vector<unsigned int>(number_levels);

	unsigned int pred;
	unsigned int arrival_time;
	static unsigned int shaping;   //new static
	unsigned int enq;
	unsigned int pkt_ptr;  //new static
	unsigned int deq;
	static unsigned int use_updated_rank;  //new static
	static unsigned int last_force_deq;  //new static
	unsigned int force_deq;
	static unsigned int force_deq_flow_id;  //new static
	static unsigned int enable_error_correction;   //new static
	static std::queue<unsigned int> pkt_ptr_queue;

	static int start_time;
	static int last_time;

	static	std::vector<unsigned int> quota_each_queue;

	static	std::vector<unsigned int> quantums;

	static std::mutex quota_mutex;

	void pass_rank_values(const Data& rank_value, const Data& level_id)
	{
		pkt_levels_ranks.erase(pkt_levels_ranks.begin() + level_id.get<uint32_t>());
		pkt_levels_ranks.insert(pkt_levels_ranks.begin() + level_id.get<uint32_t>(), rank_value.get<uint32_t>());
	}
	void pass_updated_rank_values(const Data& rank_value, const Data& flow_id, const Data& level_id)
	{
		new_ranks_each_level.erase(new_ranks_each_level.begin() + flow_id.get<uint32_t>() + (number_of_pkts_per_queue_each_level[0]*number_of_queues_per_level[0]*level_id.get<uint32_t>()));
		new_ranks_each_level.insert(new_ranks_each_level.begin() + flow_id.get<uint32_t>() + (number_of_pkts_per_queue_each_level[0]*number_of_queues_per_level[0]*level_id.get<uint32_t>()), rank_value.get<uint32_t>());
	}

	void set_quantum(const Data& queue_idx, const Data& quantum_value, const Data& reset_quota_flag)
	{
		const auto idx = queue_idx.get<uint32_t>();
		const auto new_quantum = quantum_value.get<uint32_t>();
		const bool reset_quota_immediately = reset_quota_flag.get<uint32_t>() != 0;

		std::lock_guard<std::mutex> lock(quota_mutex);

		if (idx >= quantums.size())
		{
			BMLOG_ERROR("set_quantum: queue index {} out of range ({} queues configured)", idx, quantums.size());
			return;
		}

		if (new_quantum == 0)
		{
			BMLOG_ERROR("set_quantum: rejecting zero quantum for queue {}", idx);
			return;
		}

		quantums[idx] = new_quantum;

		if (idx >= quota_each_queue.size())
		{
			BMLOG_ERROR("set_quantum: queue index {} out of range for quota vector ({} entries)", idx, quota_each_queue.size());
			return;
		}

		if (reset_quota_immediately)
		{
			quota_each_queue[idx] = new_quantum;
		}
	}

	void get_quantum(const Data& queue_idx, Data& out)
	{
		const auto idx = queue_idx.get<uint32_t>();

		std::lock_guard<std::mutex> lock(quota_mutex);

		if (idx < quantums.size())
		{
			out.set(quantums[idx]);
		}
		else
		{
			BMLOG_ERROR("get_quantum: queue index {} out of range ({} queues configured)", idx, quantums.size());
			out.set(0);  // Return 0 for invalid index
		}
	}

	void my_scheduler(const Data& in_flow_id, const Data& number_of_levels_used, const Data& in_pred, const Data& in_arrival_time, const Data& in_shaping, const Data& in_enq, const Data& in_pkt_ptr, const Data& in_deq, const Data& reset_time)
	{
		// ========== DEBUG: Function called (reduced logging) ==========
		// Only log when deq=1 (dequeue operation) to reduce log size
		// Changed to debug level to reduce log file size
		if (in_deq.get<uint32_t>() == 1) {
			WRR_LOG_DEBUG(">>> my_scheduler CALLED: flow_id={}, enq={}, deq={}, pkt_ptr={}",
			            in_flow_id.get<uint32_t>(),
			            in_enq.get<uint32_t>(),
			            in_deq.get<uint32_t>(),
			            in_pkt_ptr.get<uint32_t>());
		}
		// ============================================

// copy the inputs values :: Todo : they should be removed later and just use the inputs directly.

	if(reset_time.get<uint32_t>() == 1)
	{
		time_now = 0;
	}
		flow_id = in_flow_id.get<uint32_t>();

		// pkt_levels_ranks contains the ranks of this packet at each level, levels_ranks[number_levels] for the root, and levels_ranks[0] for the leaves
		for (int i = number_of_levels_used.get<int>(); i < int(number_levels); i++)
		{
			pkt_levels_ranks.erase(pkt_levels_ranks.begin() + i);
			pkt_levels_ranks.insert(pkt_levels_ranks.begin() + i, pkt_levels_ranks[number_of_levels_used.get<int>()-1]);
		}

		pred = in_pred.get<uint32_t>();
		arrival_time = in_arrival_time.get<uint32_t>();
		shaping = in_shaping.get<uint32_t>();
		enq = in_enq.get<uint32_t>();
		pkt_ptr = in_pkt_ptr.get<uint32_t>();
		pkt_ptr_queue.push(pkt_ptr);
		deq = in_deq.get<uint32_t>();
		force_deq = 0;
// the core code of the AR-PIFO scheduler, that enqueue, dequeue or force dequeue packets.
		run_core();
	}

// the function for enqueue/dequeue to/from the third level of the hierarchy.

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

void level_controller(std::shared_ptr<packet>& level_packet_ptr, unsigned int level_enq, unsigned int level_id)
	{
		unsigned int error_detected;
		unsigned int internal_force_flow_id;
		std::shared_ptr<packet> out_deq_pkt_ptr;
		std::shared_ptr<fifo_bank> head_FB =  NULL;
		unsigned int queue_id = 0;
		unsigned int next_flow_id_empty = 0;
		unsigned int sum_number_all_queues = 0;
		unsigned int sum_all_update_rank_flows = 0;

		for(int i = 0; i < int(level_id); i++)
		{
			if(i ==0)
			{
				sum_all_update_rank_flows = (number_of_pkts_per_queue_each_level[0]*number_of_queues_per_level[0]);
			}
			else
			{
				sum_all_update_rank_flows = sum_all_update_rank_flows + number_of_queues_per_level[i-1];
			}
			sum_number_all_queues = sum_number_all_queues + number_of_queues_per_level[i];

		}
		if (level_enq == 1)
		{
			if(level_id < (number_levels - 1))
			{
				queue_id = int(level_packet_ptr->flow_id / number_of_pkts_per_queue_each_level[level_id]);
			}

			if(level_id == 0)
			{
				head_FB = FB[queue_id];
			}

			error_detected = error_detected_each_level[queue_id + sum_number_all_queues];
			internal_force_flow_id = internal_force_flow_id_each_level[queue_id + sum_number_all_queues];

			if(level_id !=0)
			{
				sum_all_update_rank_flows = sum_all_update_rank_flows + (number_of_pkts_per_queue_each_level[0]*number_of_queues_per_level[0]) * (number_levels-1);
			}

			hier(level_packet_ptr, level_enq, head_FB,next_flow_id_empty);

			error_detected_each_level[queue_id + sum_number_all_queues] = error_detected;
			internal_force_flow_id_each_level[queue_id + sum_number_all_queues] = internal_force_flow_id;
			if(level_id == 0)
			{
				FB[queue_id] = head_FB;
			}
		}
	}


// the core function of the hier scheduler, applies enqueue and dequeue operations, to & from each level of the hirarchy,
//and each level is responsible of enqueue and dequeue in each queue inside this level
	void run_core()
	{
		// ========== DEBUG: run_core called (reduced logging) ==========
		// Only log when deq=1 (dequeue operation) to reduce log size
		// Changed to debug level to reduce log file size
		if (deq == 1) {
			WRR_LOG_DEBUG(">>> run_core CALLED: enq={}, deq={}, switch_is_ready={}",
			            enq, deq, switch_is_ready);
		}
		// ============================================

		deq_packet_ptr = NULL;
		if (enq == 1)
		{
			if((start_time == 0)||(time_now == 0))
			{
				//start_time = std::time(0);
				start_time = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now().time_since_epoch()).count();
				//for (int i = 0; i<100 ;i++)
				//{
				//	quota_each_queue.erase(quota_each_queue.begin() + i);
				//	quota_each_queue.insert(quota_each_queue.begin() + i, quota);
				//}
			}

			number_of_enqueue_packets = number_of_enqueue_packets + 1;
			std::shared_ptr<packet> enq_packet_ptr;
			enq_packet_ptr = std::make_shared<packet>();
			enq_packet_ptr->level3_flow_id = flow_id;
			enq_packet_ptr->flow_id = flow_id;
			enq_packet_ptr->rank = pkt_levels_ranks[0];
			enq_packet_ptr->pred = pred;
			enq_packet_ptr->pkt_ptr = pkt_ptr;
			enq_packet_ptr->levels_ranks = pkt_levels_ranks;
			enq_packet_ptr->arrival_time = arrival_time;

			// ========== DEBUG LOG: Enqueue (reduced logging) ==========
			// Commented out to reduce log size - enqueue happens frequently
			// bm::Logger::get()->info("========================================");
			// bm::Logger::get()->info("WRR Enqueue Operation");
			// bm::Logger::get()->info("flow_id: {}, rank: {}, pred: {}, pkt_ptr: {}",
			//             flow_id, pkt_levels_ranks[0], pred, pkt_ptr);
			// ========================================

			level_controller(enq_packet_ptr, enq, 0);

		}

		if ((deq == 1)&&(switch_is_ready == 1))
		{
			// ========== DEBUG LOG: WRR Dequeue Start (debug level to reduce log size) ==========
			WRR_LOG_DEBUG("========================================");
			WRR_LOG_DEBUG("WRR Dequeue Operation Started");
			WRR_LOG_DEBUG("Condition check: deq={}, switch_is_ready={}", deq, switch_is_ready);
			// ===================================================

			//last_time = std::time(0);
			last_time = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now().time_since_epoch()).count();

			if(last_time > start_time)
			{
				time_now = last_time - start_time;
			}
			else
			{
				time_now = 0;
			}

			//std::this_thread::sleep_for(std::chrono::microseconds(810));  // 810 equivalent to 1ms (with adding the overhead of the code)
			std::this_thread::sleep_for(std::chrono::milliseconds(10));  // equivalent to 1ms (with adding the overhead of the code)

			deq_packet_ptr = NULL;
			bool dequeued_done_right = false;
			unsigned int dequeue_right_id = 0;
			unsigned int dequeue_id = 0;
			unsigned int new_quota;
			std::shared_ptr<fifo_bank> head_FS = NULL;

			// ========== DEBUG: Check FB[0] status (verbose logging only) ==========
			WRR_LOG_VERBOSE(debug, "time_now: {}", time_now);
			WRR_LOG_VERBOSE(debug, "Initial quota_each_queue: [{}, {}, {}]",
			            quota_each_queue[0], quota_each_queue[1], quota_each_queue[2]);
			WRR_LOG_VERBOSE(debug, "quantums: [{}, {}, {}]",
			            quantums[0], quantums[1], quantums[2]);

			if(FB[0] == NULL) {
				WRR_LOG_WARN("WARNING: FB[0] is NULL - no packets in buffer!");
			} else {
				WRR_LOG_VERBOSE(debug, "FB[0] is not NULL, checking for packets...");
				std::shared_ptr<fifo_bank> debug_FB = FB[0];
				int packet_count = 0;
				while(debug_FB != NULL) {
					if(debug_FB->left != NULL && debug_FB->left->object != NULL) {
						packet_count++;
						WRR_LOG_VERBOSE(debug, "  Found packet in FB[0]: flow_id={}, rank={}, pred={}",
						            debug_FB->left->object->flow_id,
						            debug_FB->left->object->levels_ranks[0],
						            debug_FB->left->object->pred);
					}
					debug_FB = debug_FB->bottom;
				}
				WRR_LOG_VERBOSE(debug, "Total packets in FB[0]: {}", packet_count);
			}
			// ===============================================

		//if(time_now >= 200000)
		{
			const auto queue_count = static_cast<int>(quantums.size());
			if(queue_count == 0)
			{
				return;
			}
			for (int i = 0; i < queue_count; i++)
			{
				head_FS = FB[0];
				bool found_flow_i = false;
				while((head_FS != NULL))
				{
					if(head_FS->left != NULL)
					{
						if(head_FS->left->object->flow_id == i)
						{
							found_flow_i = true;
							unsigned int packet_rank = head_FS->left->object->levels_ranks[0];
							bool quota_check = quota_each_queue[i] >= packet_rank;

							// ========== DEBUG LOG: First Round Check (verbose only) ==========
							WRR_LOG_VERBOSE(debug, "First Round - Flow {}: quota={}, rank={}, check={}",
							            i, quota_each_queue[i], packet_rank, quota_check);
							// ==================================================

							if(quota_check)
							{
								dequeued_done_right = true;
								dequeue_right_id = head_FS->left->object->flow_id;
								WRR_LOG_INFO("First Round - Flow {} SELECTED for dequeue!", i);
								break;
							}
						}
					}
					head_FS = head_FS->bottom;
				}
				if(!found_flow_i) {
					WRR_LOG_VERBOSE(debug, "First Round - Flow {}: NO PACKET FOUND in FB[0]", i);
				}
				if(dequeued_done_right == true)
				{
					break;
				}
			}
			if(dequeued_done_right == false)
			{
				WRR_LOG_VERBOSE(debug, "First Round: No packet selected, entering Second Round");
				for (int i = 0; i < queue_count; i++)
				{
					unsigned int current_quota = quota_each_queue[i];
					bool quota_reset = false;

					// ========== Check queue status BEFORE quota reset ==========
					std::shared_ptr<fifo_bank> check_FB = FB[0];
					bool has_packets = false;
					unsigned int packet_count_in_flow = 0;
					while(check_FB != NULL)
					{
						if(check_FB->flow_id == i)
						{
							// Found the flow, count packets in its queue
							if(check_FB->left != NULL)
							{
								has_packets = true;
								std::shared_ptr<fifo_bank> count_ptr = check_FB->left;
								while(count_ptr != NULL)
								{
									packet_count_in_flow++;
									count_ptr = count_ptr->left;
								}
							}
							break;
						}
						check_FB = check_FB->bottom;
					}
					// ==========================================================

					if(current_quota < quantums[i])
					{
						WRR_LOG_INFO("Second Round - Flow {}: BEFORE quota reset - quota={}, quantum={}, has_packets={}, packet_count={}",
						            i, current_quota, quantums[i], has_packets, packet_count_in_flow);
						quota_each_queue.erase(quota_each_queue.begin() + i);
						quota_each_queue.insert(quota_each_queue.begin() + i, quantums[i]);
						quota_reset = true;

						// ========== DEBUG LOG: Quota Reset (reduced logging) ==========
						// Commented out to reduce log size - uncomment if needed for debugging
						// bm::Logger::get()->info("Second Round - Flow {}: quota reset from {} to {}",
						//             i, current_quota, quantums[i]);
						// ============================================
					}
					else
					{
						// Flow doesn't need quota reset, but log its status anyway
						WRR_LOG_DEBUG("Second Round - Flow {}: NO quota reset needed - quota={}, quantum={}, has_packets={}, packet_count={}",
						            i, current_quota, quantums[i], has_packets, packet_count_in_flow);
					}

					head_FS = FB[0];
					bool found_flow_i_second = false;
					while((head_FS != NULL) &&(dequeued_done_right == false))
					{
						if(head_FS->left != NULL)
						{
							if(head_FS->left->object->flow_id == i)
							{
								found_flow_i_second = true;
								unsigned int packet_rank = head_FS->left->object->levels_ranks[0];
								bool quota_check = quota_each_queue[i] >= packet_rank;

								// ========== DEBUG LOG: Second Round Check (verbose only) ==========
								WRR_LOG_VERBOSE(debug, "Second Round - Flow {}: quota={}, rank={}, check={}",
								            i, quota_each_queue[i], packet_rank, quota_check);
								// =================================================

								if(quota_check)
								{
									dequeued_done_right = true;
									dequeue_right_id = head_FS->left->object->flow_id;
									WRR_LOG_INFO("Second Round - Flow {} SELECTED for dequeue!", i);
								}
							}
						}
						head_FS = head_FS->bottom;
					}
					if(!found_flow_i_second) {
						WRR_LOG_VERBOSE(debug, "Second Round - Flow {}: NO PACKET FOUND in FB[0]", i);
					}
				}
			}
			if((dequeued_done_right == true))
			{
				WRR_LOG_VERBOSE(debug, "Calling dequeue_FB: flow_id={}, time_now={}", dequeue_right_id, time_now);
				dequeue_id = dequeue_right_id;

				// ========== Print all flow information BEFORE dequeue ==========
				WRR_LOG_INFO(">>> DEQUEUE - All flow status (BEFORE dequeue_FB):");
				for (unsigned int check_flow = 0; check_flow < quantums.size(); check_flow++)
				{
					std::shared_ptr<fifo_bank> check_FB = FB[0];
					bool check_has_packets = false;
					unsigned int check_packet_count = 0;
					while(check_FB != NULL)
					{
						if(check_FB->flow_id == check_flow)
						{
							// Found the flow, count packets in its queue (including head packet)
							if(check_FB->left != NULL)
							{
								check_has_packets = true;
								std::shared_ptr<fifo_bank> count_ptr = check_FB->left;
								while(count_ptr != NULL)
								{
									check_packet_count++;
									count_ptr = count_ptr->left;
								}
							}
							break;
						}
						check_FB = check_FB->bottom;
					}
					WRR_LOG_INFO("  Flow {}: quota={}, quantum={}, has_packets={}, packet_count={}",
					            check_flow, quota_each_queue[check_flow], quantums[check_flow],
					            check_has_packets, check_packet_count);
				}
				// ==========================================================

				dequeue_FB(deq_packet_ptr, dequeue_id, FB[0], time_now);

				// ========== DEBUG LOG: dequeue_FB Result ==========
				if(deq_packet_ptr != NULL)
				{
					WRR_LOG_INFO(">>> DEQUEUE SUCCESS - Packet will be transmitted: flow_id={}, rank={}, pred={}, pkt_ptr={}",
					            deq_packet_ptr->flow_id,
					            deq_packet_ptr->levels_ranks[0],
					            deq_packet_ptr->pred,
					            deq_packet_ptr->pkt_ptr);

					// ========== Print all flow information after dequeue ==========
					WRR_LOG_INFO(">>> DEQUEUE - All flow status (AFTER dequeue_FB):");
					for (unsigned int check_flow = 0; check_flow < quantums.size(); check_flow++)
					{
						std::shared_ptr<fifo_bank> check_FB = FB[0];
						bool check_has_packets = false;
						unsigned int check_packet_count = 0;
						while(check_FB != NULL)
						{
							if(check_FB->flow_id == check_flow)
							{
								// Found the flow, count packets in its queue
								if(check_FB->left != NULL)
								{
									check_has_packets = true;
									std::shared_ptr<fifo_bank> count_ptr = check_FB->left;
									while(count_ptr != NULL)
									{
										check_packet_count++;
										count_ptr = count_ptr->left;
									}
								}
								break;
							}
							check_FB = check_FB->bottom;
						}
						WRR_LOG_INFO("  Flow {}: quota={}, quantum={}, has_packets={}, packet_count={}",
						            check_flow, quota_each_queue[check_flow], quantums[check_flow],
						            check_has_packets, check_packet_count);
					}
					// ==========================================================
				}
				else
				{
					WRR_LOG_DEBUG("dequeue_FB FAILED: returned NULL (pred check failed?)");
				}
				// ==================================================
			}
			else
			{
				WRR_LOG_VERBOSE(debug, "No packet selected for dequeue (dequeued_done_right=false)");
			}

			if (deq_packet_ptr != NULL)
			{
				unsigned int old_quota = quota_each_queue[dequeue_id];
				new_quota = quota_each_queue[dequeue_id] - deq_packet_ptr->levels_ranks[0];
				quota_each_queue.erase(quota_each_queue.begin() + dequeue_id);
				quota_each_queue.insert(quota_each_queue.begin() + dequeue_id, new_quota);

				// ========== DEBUG LOG: Quota Update (debug level to reduce log size) ==========
				WRR_LOG_DEBUG("Quota Updated - Flow {}: {} - {} = {}",
				            dequeue_id, old_quota, deq_packet_ptr->levels_ranks[0], new_quota);
				WRR_LOG_DEBUG("Updated quota_each_queue: [{}, {}, {}]",
				            quota_each_queue[0], quota_each_queue[1], quota_each_queue[2]);
				// ============================================
			}
			else if (dequeued_done_right == true)
			{
				WRR_LOG_WARN("WARNING: dequeued_done_right=true but deq_packet_ptr=NULL");
				WRR_LOG_DEBUG("Resetting all quotas to quantums");

				for (int i = queue_count - 1; i >= 0; i--)
				{
//BMLOG_DEBUG("Invoked ELBEDIWY testing of starting the dequeue operation i = {}, current_quota = {}, quantums[i] = {}", i, current_quota, quantums[i])
						quota_each_queue.erase(quota_each_queue.begin() + i);
						quota_each_queue.insert(quota_each_queue.begin() + i, quantums[i]);
				}
			}
		}  // end unconditional dequeue scope (was guarded by commented if)
		}  // end if ((deq == 1) && (switch_is_ready == 1))
		else
		{
			// ========== DEBUG: Dequeue condition not met (debug level to reduce log size) ==========
			WRR_LOG_DEBUG("Dequeue condition NOT met: deq={}, switch_is_ready={}",
			            deq, switch_is_ready);
			// ======================================================
		}
	}


// This is the AR-PIFO queue function which handles 1 flow_scheduler and 1 FIFO at a time, this function is used by each level function
	void hier(std::shared_ptr<hier_scheduler::packet> pkt_ptr, unsigned int in_enq, std::shared_ptr<hier_scheduler::fifo_bank>& in_head_FB, unsigned int& next_flow_id_empty)
	{
		std::shared_ptr<hier_scheduler::packet> deq_packet_ptr = NULL;
		std::shared_ptr<hier_scheduler::flow_scheduler> cur_ptr_FS;
		next_flow_id_empty = 0;

// in case of enqueue (enq ==1), a packet will be enqueued to flow scheduler first enqueue_FS (if its flow already existed there), it will be enqueued in the FIFO bank instead.
// in case of dequeue (deq ==1), a packet will be dequeued from the flow scheduler dequeue_FS, then the next packet from the same flow will be dequeued from the FIFO bank dequeue_FB,
// then enqueue this next packet to the flow scheduler enqueue_FS.
		if (in_enq == 1)
		{
			std::shared_ptr<hier_scheduler::packet> enq_packet_ptr;
			enq_packet_ptr = std::shared_ptr<hier_scheduler::packet>(std::make_shared<hier_scheduler::packet>(*pkt_ptr));
			enqueue_FB(enq_packet_ptr, in_head_FB);

		}
	}


// used by AR-PIFO function to enqueue inside a certain FIFO bank
	void enqueue_FB(std::shared_ptr<hier_scheduler::packet> new_packet_ptr, std::shared_ptr<hier_scheduler::fifo_bank>& head_FB)
	{
		std::shared_ptr<hier_scheduler::fifo_bank> cur_ptr_FB;
		cur_ptr_FB = std::shared_ptr<hier_scheduler::fifo_bank>(std::make_shared<hier_scheduler::fifo_bank>());
		std::shared_ptr<hier_scheduler::fifo_bank> prev_ptr_FB;
		prev_ptr_FB = std::shared_ptr<hier_scheduler::fifo_bank>(std::make_shared<hier_scheduler::fifo_bank>());
		std::shared_ptr<hier_scheduler::fifo_bank> temp_ptr;
		temp_ptr = std::shared_ptr<hier_scheduler::fifo_bank>(std::make_shared<hier_scheduler::fifo_bank>());
		temp_ptr->object = new_packet_ptr;
		temp_ptr->left = NULL;
		temp_ptr->bottom = NULL;
		if (head_FB == NULL)
		{
			head_FB = std::shared_ptr<hier_scheduler::fifo_bank>(std::make_shared<hier_scheduler::fifo_bank>());
			head_FB->flow_id = new_packet_ptr->flow_id;
			head_FB->bottom = NULL;
			head_FB->left = temp_ptr;
			cur_ptr_FB = head_FB;
		}
		else
		{
			cur_ptr_FB = head_FB;
			prev_ptr_FB = NULL;
			unsigned int flow_id_FB_found = 0;
			while (cur_ptr_FB != NULL)
			{
				if (cur_ptr_FB->flow_id == new_packet_ptr->flow_id)
				{
					flow_id_FB_found = 1;
					while (cur_ptr_FB->left != NULL)
					{
						cur_ptr_FB = cur_ptr_FB->left;
					}
					cur_ptr_FB->left = temp_ptr;
					break;
				}
				prev_ptr_FB = cur_ptr_FB;
				cur_ptr_FB = cur_ptr_FB->bottom;
			}
			if (flow_id_FB_found == 0)
			{
				std::shared_ptr<hier_scheduler::fifo_bank> temp_ptr2;
				temp_ptr2 = std::shared_ptr<hier_scheduler::fifo_bank>(std::make_shared<hier_scheduler::fifo_bank>());
				temp_ptr2->flow_id = new_packet_ptr->flow_id;
				temp_ptr2->left = temp_ptr;
				temp_ptr2->bottom = NULL;
				prev_ptr_FB->bottom = temp_ptr2;
			}
		}

	}
// used by AR-PIFO function to dequeue from a certain FIFO bank
	void dequeue_FB(std::shared_ptr<hier_scheduler::packet>& deq_packet_ptr, unsigned int flow_id, std::shared_ptr<hier_scheduler::fifo_bank>& head_FB, unsigned int in_time)
	{
		std::shared_ptr<hier_scheduler::fifo_bank> cur_ptr_FB;
		cur_ptr_FB = std::shared_ptr<hier_scheduler::fifo_bank>(std::make_shared<hier_scheduler::fifo_bank>());
		deq_packet_ptr = NULL;
		cur_ptr_FB = head_FB;

		// ========== DEBUG LOG: dequeue_FB Start ==========
		// Reduced logging - uncomment if needed for debugging
		// bm::Logger::get()->info("dequeue_FB called: flow_id={}, in_time={}", flow_id, in_time);
		// ==================================================

		while (cur_ptr_FB != NULL)
		{
			if ((cur_ptr_FB->flow_id == flow_id) && (cur_ptr_FB->left != NULL))
			{
				if(cur_ptr_FB->left->object != NULL)
				{
					unsigned int packet_pred = cur_ptr_FB->left->object->pred;
					bool pred_check = packet_pred <= in_time;

					// ========== DEBUG LOG: pred Check (reduced logging) ==========
					// Commented out to reduce log size - uncomment if needed for debugging
					// bm::Logger::get()->info("dequeue_FB - pred check: {} <= {} = {}",
					//             packet_pred, in_time, pred_check);
					// ===========================================

					if(pred_check)
					{
						deq_packet_ptr = cur_ptr_FB->left->object;
						cur_ptr_FB->left = cur_ptr_FB->left->left;
						// Reduced logging - uncomment if needed for debugging
						// bm::Logger::get()->info("dequeue_FB - Packet dequeued successfully");
					}
					else
					{
						// Reduced logging - uncomment if needed for debugging
						// bm::Logger::get()->info("dequeue_FB - pred check FAILED, packet NOT dequeued");
					}
				}

				break;
			}
			cur_ptr_FB = cur_ptr_FB->bottom;
		}

		if(deq_packet_ptr == NULL)
		{
			// Reduced logging - uncomment if needed for debugging
			// bm::Logger::get()->info("dequeue_FB - No packet found for flow_id={}", flow_id);
		}
	}

// return the last enqueued packet pointer to be used in the buffer inside the "Simple_switch" target
	unsigned int get_last_pkt_ptr()
	{
		if(!pkt_ptr_queue.empty())
		{
			unsigned int current_pkt_ptr = pkt_ptr_queue.front();
			pkt_ptr_queue.pop();
			number_of_read_packets = number_of_read_packets + 1;
			return current_pkt_ptr;
		}
		else
		{
			return 0;
		}
	}

// Apply dequeue operation in the scheduler, will be used inside the "Simple_Switch" target
	unsigned int dequeue_my_scheduler()
	{
		// ========== DEBUG: dequeue_my_scheduler called (debug level to reduce log size) ==========
		WRR_LOG_DEBUG(">>> dequeue_my_scheduler CALLED");
		WRR_LOG_DEBUG("    number_of_deq_pkts={}, num_of_read_pkts={}, number_of_enq_pkts={}",
		            number_of_dequeue_packets, number_of_read_packets, number_of_enqueue_packets);
		WRR_LOG_DEBUG("    switch_is_ready={}", switch_is_ready);
		// ========================================================

	flow_id = 0;
	pred = 0;
	enq = 0;
	unsigned int null_ptr = 0;
	force_deq = last_force_deq;
	if(force_deq ==0)
	deq = 1;
	else
	deq = 0;

	WRR_LOG_DEBUG("    Setting deq={}, force_deq={}", deq, force_deq);

	run_core();

	if(deq_packet_ptr != NULL)
	{
		switch_is_ready = 0;

		if(last_force_deq !=0)
		last_force_deq = 0;
		if(force_deq_flow_id !=0)
		force_deq_flow_id = 0;
		//if(pkt_ptr !=0)
		//pkt_ptr = 0;
		return deq_packet_ptr->pkt_ptr;
	}
	else
	{
	return null_ptr;
	}
	}

// return the number of enqueued packets until now to the "Simple_Switch".
	unsigned int number_of_enq_pkts()
	{
		return number_of_enqueue_packets;
	}


	unsigned int number_of_deq_pkts()
	{
		return number_of_dequeue_packets;
	}

// return the number of captured packets until now by the TM_buffer.h.
	unsigned int num_of_read_pkts()
	{
		return number_of_read_packets;
	}

// A flag from the target switch, indicating that the switch is ready to receive a new dequeued pkt from the TM
	void start_dequeue(unsigned int start)
	{
		switch_is_ready = start;
	}

// reset the number of enqueued packets to zero by the "Simple_Switch"
	void reset_number_of_enq_pkts()
	{
		number_of_enqueue_packets = 0;
	}

	void increment_deq_count()
	{
		number_of_dequeue_packets = number_of_dequeue_packets + 1;
	}

 private:
  // Attribute
  Data verbose{};

  // Data members
  bool verbose_{false};
};

}  // namespace bm
#endif
