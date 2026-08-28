# import asyncio
# from firebase_config import db, send_fcm_notification

# async def process_cascading_sos(sos_id: str, target_users: list[str]):
#     tier1 = target_users[:3]      
#     tier2 = target_users[3:8]     
#     tier3 = target_users[8:]      

#     # --- WAVE 1 ---
#     print(f"\n🚀 [WAVE 1] SOS {sos_id} Triggered!")
#     await update_wave_status(sos_id, "WAVE 1: Alerting Primary Contacts")
#     await notify_tier_users(tier1, "🚨 URGENT: Nearby Emergency!", "Tier 1: Assist needed immediately!", sos_id)

#     print("⏳ Waiting 30 seconds for Tier 1...")
#     await asyncio.sleep(30)
    
#     if not is_sos_active(sos_id): return

#     # --- WAVE 2 ---
#     print(f"\n🌊 [WAVE 2] Escalating SOS {sos_id}!")
#     await update_wave_status(sos_id, "WAVE 2: Expanding to Nearby Contacts")
#     await notify_tier_users(tier2, "🚨 ESCALATED: Emergency Unresolved!", "Tier 2: Please assist!", sos_id)

#     print("⏳ Waiting 30 seconds for Tier 2...")
#     await asyncio.sleep(30)

#     if not is_sos_active(sos_id): return

#     # --- WAVE 3 ---
#     print(f"\n🌋 [WAVE 3] Area-wide Critical Alert for SOS {sos_id}!")
#     await update_wave_status(sos_id, "WAVE 3: Area-wide Critical Alert")
#     await notify_tier_users(tier3, "🚨 CRITICAL: Area-wide Alert!", "Tier 3: All nearby volunteers required!", sos_id)

# async def update_wave_status(sos_id: str, wave_text: str):
#     """Updates Firestore so the Flutter UI can listen to the changes in real-time."""
#     try:
#         db.collection('sos_alerts').document(sos_id).update({'currentWave': wave_text})
#     except Exception as e:
#         print(f"⚠️ Error updating wave status: {e}")

# def is_sos_active(sos_id: str) -> bool:
#     try:
#         doc = db.collection('sos_alerts').document(sos_id).get()
#         return doc.exists and doc.to_dict().get('status') == 'ACTIVE'
#     except:
#         return True

# async def notify_tier_users(user_ids: list[str], title: str, body: str, sos_id: str):
#     for uid in user_ids:
#         try:
#             user_doc = db.collection('Users').document(uid).get()
#             if not user_doc.exists:
#                 user_doc = db.collection('users').document(uid).get()

#             if user_doc.exists:
#                 fcm_token = user_doc.to_dict().get('fcmToken')
#                 if fcm_token:
#                     send_fcm_notification(fcm_token, title, body, {"sosId": sos_id, "type": "SOS_ALERT"})
#                 else:
#                     print(f"⚠️ No fcmToken found for user: {uid}")
#         except Exception as e:
#             print(f"❌ Error notifying user {uid}: {e}")

import asyncio
from firebase_config import db, send_fcm_notification

async def process_cascading_sos(sos_id: str, target_users: list[str]):
    # Note: Consider having Flutter send these lists explicitly in the future
    tier1 = target_users[:3]      
    tier2 = target_users[3:8]     
    tier3 = target_users[8:]      

    # --- WAVE 1 ---
    print(f"\n🚀 [WAVE 1] SOS {sos_id} Triggered!")
    await asyncio.to_thread(update_wave_status_sync, sos_id, "WAVE 1: Alerting Primary Contacts")
    await notify_tier_users(tier1, "🚨 URGENT: Nearby Emergency!", "Tier 1: Assist needed immediately!", sos_id)

    print("⏳ Waiting 30 seconds for Tier 1...")
    await asyncio.sleep(30)
    
    if not await asyncio.to_thread(is_sos_active_sync, sos_id): return

    # --- WAVE 2 ---
    print(f"\n🌊 [WAVE 2] Escalating SOS {sos_id}!")
    await asyncio.to_thread(update_wave_status_sync, sos_id, "WAVE 2: Expanding to Nearby Contacts")
    await notify_tier_users(tier2, "🚨 ESCALATED: Emergency Unresolved!", "Tier 2: Please assist!", sos_id)

    print("⏳ Waiting 30 seconds for Tier 2...")
    await asyncio.sleep(30)

    if not await asyncio.to_thread(is_sos_active_sync, sos_id): return

    # --- WAVE 3 ---
    print(f"\n🌋 [WAVE 3] Area-wide Critical Alert for SOS {sos_id}!")
    await asyncio.to_thread(update_wave_status_sync, sos_id, "WAVE 3: Area-wide Critical Alert")
    await notify_tier_users(tier3, "🚨 CRITICAL: Area-wide Alert!", "Tier 3: All nearby volunteers required!", sos_id)


# 🔄 Separated into synchronous functions to be run safely in threads
def update_wave_status_sync(sos_id: str, wave_text: str):
    try:
        db.collection('sos_alerts').document(sos_id).update({'currentWave': wave_text})
    except Exception as e:
        print(f"⚠️ Error updating wave status: {e}")

def is_sos_active_sync(sos_id: str) -> bool:
    try:
        doc = db.collection('sos_alerts').document(sos_id).get()
        return doc.exists and doc.to_dict().get('status') == 'ACTIVE'
    except Exception as e:
        print(f"⚠️ Error checking SOS status: {e}")
        return True # Default to True to fail-safe and keep alerting

async def notify_tier_users(user_ids: list[str], title: str, body: str, sos_id: str):
    if not user_ids: return

    try:
        # 🚀 BATCH FETCHING: Get all users in ONE single database query!
        refs = [db.collection('Users').document(uid) for uid in user_ids]
        
        # Run the synchronous batch get inside a thread
        docs = await asyncio.to_thread(db.get_all, refs)

        for doc in docs:
            if doc.exists:
                fcm_token = doc.to_dict().get('fcmToken')
                if fcm_token:
                    # Depending on the FCM library, this might also need to be run in a thread
                    # if send_fcm_notification is synchronous.
                    await asyncio.to_thread(
                        send_fcm_notification, 
                        fcm_token, title, body, {"sosId": sos_id, "type": "SOS_ALERT"}
                    )
                else:
                    print(f"⚠️ No fcmToken found for user: {doc.id}")
            else:
                print(f"⚠️ User doc not found for: {doc.id}")
                
    except Exception as e:
        print(f"❌ Error in notify_tier_users: {e}")