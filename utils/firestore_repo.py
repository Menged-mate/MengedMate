import firebase_admin
from firebase_admin import firestore
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FirestoreRepository:
    def __init__(self):
        try:
            self.db = firestore.client()
        except ValueError:
            # Handle case where app is not initialized or env vars missing
            # Ideally this is initialized in settings or firebase_config
            self.db = None
            logger.error("Firestore client could not be initialized.")

    def _get_collection(self):
        if not self.db:
            return None
        return self.db.collection('charging_stations')

    def get_station(self, station_id):
        """Retrieve a single station by ID."""
        collection = self._get_collection()
        if not collection:
            return None
        
        doc_ref = collection.document(str(station_id))
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def create_station(self, data):
        """Create a new station document."""
        collection = self._get_collection()
        if not collection:
            return None
            
        # Ensure ID exists
        station_id = str(data.get('id', uuid.uuid4()))
        data['id'] = station_id
        
        # Add timestamps
        data['created_at'] = datetime.utcnow().isoformat()
        data['updated_at'] = datetime.utcnow().isoformat()

        # Handle typically non-serializable fields if coming from Django objects
        # For now assuming 'data' is a clean dict
        
        doc_ref = collection.document(station_id)
        doc_ref.set(data)
        return data

    def update_station(self, station_id, data):
        """Update an existing station."""
        collection = self._get_collection()
        if not collection:
            return None

        doc_ref = collection.document(str(station_id))
        
        # Determine if it exists first
        if not doc_ref.get().exists:
            return None

        data['updated_at'] = datetime.utcnow().isoformat()
        doc_ref.update(data)
        
        # Return full object
        return self.get_station(station_id)

    def delete_station(self, station_id):
        """Delete a station."""
        collection = self._get_collection()
        if not collection:
            return False
            
        collection.document(str(station_id)).delete()
        return True

    def _get_connectors_collection(self, station_id):
        station_ref = self._get_collection().document(str(station_id))
        return station_ref.collection('connectors')

    def get_connector(self, station_id, connector_id):
        col = self._get_connectors_collection(station_id)
        doc = col.document(str(connector_id)).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def create_connector(self, station_id, data):
        col = self._get_connectors_collection(station_id)
        connector_id = str(data.get('id', uuid.uuid4()))
        data['id'] = connector_id
        col.document(connector_id).set(data)
        
        # Update station counts
        self._update_station_counts(station_id)
        return data

    def update_connector(self, station_id, connector_id, data):
        col = self._get_connectors_collection(station_id)
        doc_ref = col.document(str(connector_id))
        if not doc_ref.get().exists:
            return None
        doc_ref.update(data)
        
        # Update station counts
        self._update_station_counts(station_id)
        return self.get_connector(station_id, connector_id)

    def delete_connector(self, station_id, connector_id):
        col = self._get_connectors_collection(station_id)
        col.document(str(connector_id)).delete()
        self._update_station_counts(station_id)
        return True
        
    def list_connectors(self, station_id):
        col = self._get_connectors_collection(station_id)
        return [dict(d.to_dict(), id=d.id) for d in col.stream()]

    def _update_station_counts(self, station_id):
        """Recalculate total/available connectors for station."""
        connectors = self.list_connectors(station_id)
        total = sum(c.get('quantity', 0) for c in connectors)
        available = sum(c.get('available_quantity', 0) for c in connectors)
        
        self.update_station(station_id, {
            'total_connectors': total,
            'available_connectors': available
        })

    def _get_images_collection(self, station_id):
        station_ref = self._get_collection().document(str(station_id))
        return station_ref.collection('images')

    def create_image(self, station_id, data):
        col = self._get_images_collection(station_id)
        image_id = str(data.get('id', uuid.uuid4()))
        data['id'] = image_id
        col.document(image_id).set(data)
        return data

    def list_images(self, station_id):
        col = self._get_images_collection(station_id)
        return [dict(d.to_dict(), id=d.id) for d in col.stream()]

    def _get_reviews_collection(self, station_id):
        station_ref = self._get_collection().document(str(station_id))
        return station_ref.collection('reviews')

    def create_review(self, station_id, data):
        col = self._get_reviews_collection(station_id)
        review_id = str(data.get('id', uuid.uuid4()))
        data['id'] = review_id
        data['station_id'] = str(station_id) # Store station_id for Collection Group Queries
        col.document(review_id).set(data)
        
        # Update station rating
        self._update_station_rating(station_id)
        return data

    def get_review(self, station_id, review_id):
        col = self._get_reviews_collection(station_id)
        doc = col.document(str(review_id)).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def list_reviews(self, station_id):
        col = self._get_reviews_collection(station_id)
        # Sort by created_at desc
        query = col.order_by('created_at', direction=firestore.Query.DESCENDING)
        return [dict(d.to_dict(), id=d.id) for d in query.stream()]
        
    def list_reviews_by_user(self, user_id):
        """List reviews by a specific user across all stations."""
        # Using Collection Group Query
        # Note: Requires composite index in Firestore usually? 
        # For single field equality 'user_id', it should be fine.
        client = self.client
        if not client: return []
        
        # 'reviews' is the collection ID
        reviews = client.collection_group('reviews').where('user_id', '==', str(user_id)).stream()
        return [dict(d.to_dict(), id=d.id) for d in reviews]

    def list_reviews_by_owner(self, owner_id):
        """List reviews for stations owned by owner_id."""
        # We stored 'owner_id' on review? No, not yet.
        # Efficient way: add owner_id to review data.
        client = self.client
        if not client: return []
        
        reviews = client.collection_group('reviews').where('station_owner_id', '==', str(owner_id)).stream()
        return [dict(d.to_dict(), id=d.id) for d in reviews]

    def update_review(self, station_id, review_id, data):
        col = self._get_reviews_collection(station_id)
        col.document(str(review_id)).update(data)
        self._update_station_rating(station_id)
        return self.get_review(station_id, review_id)

    def delete_review(self, station_id, review_id):
        col = self._get_reviews_collection(station_id)
        col.document(str(review_id)).delete()
        self._update_station_rating(station_id)
        return True

    def _update_station_rating(self, station_id):
        reviews = self.list_reviews(station_id)
        # Filter active reviews if we had a flag, but assuming all in firestore are active or we filter in list
        if not reviews:
            self.update_station(station_id, {'rating': 0.0, 'rating_count': 0})
            return

        total_rating = sum(float(r.get('rating', 0)) for r in reviews)
        count = len(reviews)
        avg = total_rating / count if count > 0 else 0
        
        self.update_station(station_id, {
            'rating': round(avg, 2),
            'rating_count': count
        })

    # --- User Management ---
    
    def _get_users_collection(self):
        return self.db.collection('users')

    def _get_user_ref(self, user_id):
        return self._get_users_collection().document(str(user_id))

    def create_user_profile(self, user_id, data):
        """Create or overwrite user profile."""
        # Ensure user_id is string
        uid = str(user_id)
        data['id'] = uid
        self._get_user_ref(uid).set(data, merge=True)
        return data

    def get_user_profile(self, user_id):
        doc = self._get_user_ref(user_id).get()
        if doc.exists:
            return doc.to_dict()
        return None

    def update_user_profile(self, user_id, data):
        self._get_user_ref(user_id).update(data)
        return self.get_user_profile(user_id)

    # ... (Vehicle Management uses _get_users_collection directly or can switch to helper, but sticking to provided context)

    # ---------------------------------------------------------
    # Station Owner Management
    # ---------------------------------------------------------
    def _get_station_owners_collection(self):
        return self.db.collection('station_owners')

    def create_station_owner(self, user_id, data):
        """Create station owner profile keyed by user_id."""
        # Enforce ID = user_id for 1:1 mapping
        owner_id = str(user_id)
        data['id'] = owner_id
        data['user_id'] = owner_id
        data['created_at'] = datetime.utcnow().isoformat()
        data['updated_at'] = datetime.utcnow().isoformat()
        
        self._get_station_owners_collection().document(owner_id).set(data)
        return data

    def get_station_owner(self, user_id):
        """Get station owner profile by user_id."""
        doc = self._get_station_owners_collection().document(str(user_id)).get()
        if doc.exists:
            return dict(doc.to_dict(), id=doc.id)
        return None

    def update_station_owner(self, user_id, data):
        """Update station owner profile."""
        data['updated_at'] = datetime.utcnow().isoformat()
        self._get_station_owners_collection().document(str(user_id)).update(data)
        return self.get_station_owner(user_id)


    # --- Vehicle Management ---

    def _get_vehicles_collection(self, user_id):
        return self._get_users_collection().document(str(user_id)).collection('vehicles')

    def list_vehicles(self, user_id):
        col = self._get_vehicles_collection(user_id)
        return [dict(d.to_dict(), id=d.id) for d in col.stream()]
        
    def get_vehicle(self, user_id, vehicle_id):
        col = self._get_vehicles_collection(user_id)
        doc = col.document(str(vehicle_id)).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def create_vehicle(self, user_id, data):
        col = self._get_vehicles_collection(user_id)
        veh_id = str(data.get('id', uuid.uuid4()))
        data['id'] = veh_id
        col.document(veh_id).set(data)
        return data

    def update_vehicle(self, user_id, vehicle_id, data):
        col = self._get_vehicles_collection(user_id)
        col.document(str(vehicle_id)).update(data)
        return self.get_vehicle(user_id, vehicle_id)

    def delete_vehicle(self, user_id, vehicle_id):
        col = self._get_vehicles_collection(user_id)
        col.document(str(vehicle_id)).delete()
        return True

    # --- Support Management ---

    def _get_tickets_collection(self):
        return self.db.collection('support_tickets')
        
    def _get_faqs_collection(self):
        return self.db.collection('faqs')

    def create_ticket(self, data):
        data['created_at'] = datetime.now().isoformat()
        data['updated_at'] = datetime.now().isoformat()
        data['status'] = 'open'
        
        # Auto-assign ID
        _, doc_ref = self._get_tickets_collection().add(data)
        data['id'] = doc_ref.id
        # Update doc with ID for easier fetching if needed, though ID is doc key
        return data

    def list_user_tickets(self, user_id):
        # Query by user_id
        # Requires index ideally, but small scale generic query works
        col = self._get_tickets_collection()
        query = col.where('user_id', '==', str(user_id))
        return [dict(d.to_dict(), id=d.id) for d in query.stream()]
        
    def list_faqs(self, category=None):
        col = self._get_faqs_collection()
        query = col.where('is_active', '==', True)
        if category:
            query = query.where('category', '==', category)
            
        return [dict(d.to_dict(), id=d.id) for d in query.stream()]
    
    def get_faq(self, faq_id):
        doc = self._get_faqs_collection().document(str(faq_id)).get()
        if doc.exists:
            return dict(doc.to_dict(), id=doc.id)
        return None

    # --- AI Recommendations Management ---

    def _get_recommendations_collection(self, user_id):
        return self._get_users_collection().document(str(user_id)).collection('recommendations')

    def get_search_preferences(self, user_id):
        # Stored in user profile or separate doc? Let's use separate doc in subcollection or field in profile.
        # Let's use 'search_preferences' subcollection single doc 'default' for extensibility
        doc = self._get_users_collection().document(str(user_id)).collection('preferences').document('search').get()
        if doc.exists:
            return doc.to_dict()
        return None

    def update_search_preferences(self, user_id, data):
        ref = self._get_users_collection().document(str(user_id)).collection('preferences').document('search')
        ref.set(data, merge=True)
        return self.get_search_preferences(user_id)

    def create_recommendation_history(self, user_id, data):
        data['recommended_at'] = datetime.now().isoformat()
        col = self._get_recommendations_collection(user_id)
        _, doc_ref = col.add(data)
        data['id'] = doc_ref.id
        return data

    def list_recommendation_history(self, user_id, limit=20):
        col = self._get_recommendations_collection(user_id)
        # Order by recommended_at desc
        query = col.order_by('recommended_at', direction=firestore.Query.DESCENDING).limit(limit)
        return [dict(d.to_dict(), id=d.id) for d in query.stream()]
        
    def get_recommendation_history(self, user_id, rec_id):
        doc = self._get_recommendations_collection(user_id).document(str(rec_id)).get()
        if doc.exists:
            return dict(doc.to_dict(), id=doc.id)
        return None

    def update_recommendation_feedback(self, user_id, rec_id, data):
        self._get_recommendations_collection(user_id).document(str(rec_id)).update(data)
        return True

    def list_stations(self, filters=None, limit=20):
        """List stations with optional basic filtering."""
        collection = self._get_collection()
        if not collection:
            return []

        query = collection
        
        if filters:
            # Example filter: {'owner_id': '123'}
            for key, value in filters.items():
                query = query.where(key, '==', value)

        # Basic ordering
        # query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
        
        docs = query.limit(limit).stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            results.append(data)
            
        return results

    # ---------------------------------------------------------
    # Favorites Management
    # ---------------------------------------------------------
    def _get_favorites_collection(self, user_id):
        return self._get_user_ref(user_id).collection('favorites')

    def add_favorite(self, user_id, station_data):
        """Add a station to user favorites"""
        station_id = station_data.get('id')
        if not station_id:
            raise ValueError("Station ID is required")
            
        fav_ref = self._get_favorites_collection(user_id).document(str(station_id))
        
        # Store a snapshot of the station for quick listing
        data = {
            'station_id': str(station_id),
            'added_at': datetime.utcnow().isoformat(),
            'station_name': station_data.get('name'),
            'station_address': station_data.get('address'),
            'station_image': station_data.get('main_image'),
            'thumbnail': station_data.get('thumbnail'), # If available
            'rating': station_data.get('rating', 0),
            'latitude': station_data.get('latitude'),
            'longitude': station_data.get('longitude')
        }
        fav_ref.set(data)
        return data

    def remove_favorite(self, user_id, station_id):
        """Remove a station from favorites"""
        self._get_favorites_collection(user_id).document(str(station_id)).delete()

    def get_favorite(self, user_id, station_id):
        """Check if station is favorite"""
        doc = self._get_favorites_collection(user_id).document(str(station_id)).get()
        if doc.exists:
            return {**doc.to_dict(), 'id': doc.id}
        return None

    def list_favorites(self, user_id):
        """List user's favorite stations"""
        docs = self._get_favorites_collection(user_id).order_by('added_at', direction=firestore.Query.DESCENDING).stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

    # ---------------------------------------------------------
    # Payout Method Management
    # ---------------------------------------------------------
    def _get_payout_methods_collection(self, owner_id):
        return self._get_station_owners_collection().document(str(owner_id)).collection('payout_methods')

    def create_payout_method(self, owner_id, data):
        col = self._get_payout_methods_collection(owner_id)
        # Use auto-id or explicit if provided
        pm_id = str(data.get('id', uuid.uuid4()))
        data['id'] = pm_id
        data['created_at'] = datetime.utcnow().isoformat()
        
        # If default, unset others?
        if data.get('is_default'):
            self._unset_default_payout_method(owner_id)
            
        col.document(pm_id).set(data)
        return data

    def list_payout_methods(self, owner_id):
        col = self._get_payout_methods_collection(owner_id)
        return [dict(d.to_dict(), id=d.id) for d in col.stream()]

    def get_payout_method(self, owner_id, pm_id):
        doc = self._get_payout_methods_collection(owner_id).document(str(pm_id)).get()
        if doc.exists:
            return dict(doc.to_dict(), id=doc.id)
        return None

    def update_payout_method(self, owner_id, pm_id, data):
        col = self._get_payout_methods_collection(owner_id)
        
        if data.get('is_default'):
            self._unset_default_payout_method(owner_id)
            
        col.document(str(pm_id)).update(data)
        return self.get_payout_method(owner_id, pm_id)
        
    def delete_payout_method(self, owner_id, pm_id):
        self._get_payout_methods_collection(owner_id).document(str(pm_id)).delete()
        return True

    def _unset_default_payout_method(self, owner_id):
        """Helper to set is_default=False for all methods."""
        col = self._get_payout_methods_collection(owner_id)
        defaults = col.where('is_default', '==', True).stream()
        for doc in defaults:
            doc.reference.update({'is_default': False})

    # ---------------------------------------------------------
    # Withdrawal Management
    # ---------------------------------------------------------
    def _get_withdrawals_collection(self):
        return self.db.collection('withdrawals')

    def create_withdrawal(self, data):
        data['created_at'] = datetime.utcnow().isoformat()
        data['updated_at'] = datetime.utcnow().isoformat()
        data['status'] = 'pending'
        
        _, doc_ref = self._get_withdrawals_collection().add(data)
        data['id'] = doc_ref.id
        return data

    def get_withdrawal(self, request_id):
        doc = self._get_withdrawals_collection().document(str(request_id)).get()
        if doc.exists:
            return dict(doc.to_dict(), id=doc.id)
        return None

    def list_withdrawals(self, owner_id=None):
        col = self._get_withdrawals_collection()
        if owner_id:
            query = col.where('owner_id', '==', str(owner_id))
        else:
            query = col.order_by('created_at', direction=firestore.Query.DESCENDING)
            
        return [dict(d.to_dict(), id=d.id) for d in query.stream()]
        
    def update_withdrawal(self, request_id, data):
        data['updated_at'] = datetime.utcnow().isoformat()
        self._get_withdrawals_collection().document(str(request_id)).update(data)
        return self.get_withdrawal(request_id)

# Singleton instance
firestore_repo = FirestoreRepository()
