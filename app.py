from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, distinct
from datetime import datetime
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow import fields
from image_download import  download_image
from best_image_Z import calculate_quality_score
from nltk.util import ngrams
from google_ocr import  detect_text_from_binary
import re
import random
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///AI_image_ai.db'  # Use PostgreSQL/MySQL for prod
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

db = SQLAlchemy(app)

# ----------------------------
# Story 4: Trial Tracker Table
# ----------------------------
class TrialTracker(db.Model):
    __tablename__ = 'trial_tracker'
    
    trial_id = db.Column(db.String, primary_key=True, nullable=False)
    duplicated = db.Column(db.Boolean, nullable=False)
    number_of_clusters = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    image_clusters = db.relationship('ImageCluster', backref='trial', lazy=True)
    image_trackers = db.relationship('ImageTracker', backref='trial', lazy=True)

# ----------------------------
# Story 2: Image Cluster Table
# ----------------------------
class ImageCluster(db.Model):
    __tablename__ = 'image_cluster'
    id = db.Column(db.Integer, primary_key=True)
    image_cluster_id = db.Column(db.Text, nullable=False)
    duplicate_image = db.Column(db.Integer, nullable=False)
    display_image = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False)
    best_image = db.Column(db.Text, nullable=True)
    trial_id = db.Column(db.String, db.ForeignKey('trial_tracker.trial_id'), nullable=False)



# ----------------------------
# Story 3: Image Tracker Table
# ----------------------------
class ImageTracker(db.Model):
    __tablename__ = 'image_tracker'

    id = db.Column(db.Integer, primary_key=True)
    image_id_clin = db.Column(db.Integer, nullable=False)
    trial_id = db.Column(db.String, db.ForeignKey('trial_tracker.trial_id'), nullable=False)
    image_text = db.Column(db.Text, nullable=False)
    image_score = db.Column(db.Float, nullable=False)
    is_duplicate = db.Column(db.Boolean, nullable=False)
    image_url = db.Column(db.Text, nullable=False)
    image_reference_url = db.Column(db.Text, nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# ----------------------------
# Create All Tables
# ----------------------------
@app.route('/create-db', methods=['GET'])
def create_db():
    db.create_all()
    return jsonify({"message": "✅ All tables created successfully."})



class TrialTrackerSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = TrialTracker
        load_instance = True
        include_fk = True

    image_clusters = fields.Nested('ImageClusterSchema', many=True, exclude=('trial',))
    image_trackers = fields.Nested('ImageTrackerSchema', many=True, exclude=('trial',))

# ----------------------------
# ImageCluster Schema
# ----------------------------
class ImageClusterSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ImageCluster
        load_instance = True
        include_fk = True

    image_trackers = fields.Nested('ImageTrackerSchema', many=True, exclude=('image_cluster',))

# ----------------------------
# ImageTracker Schema
# ----------------------------
class ImageTrackerSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ImageTracker
        load_instance = True
        include_fk = True


image_tracker_schema = ImageTrackerSchema()

@app.route('/')
def home():
    return "Hello, Flask World! 🎉"

def jaccard_similarity(s1, s2, n=2):
    ngrams1 = set(ngrams(s1.split(), n))
    ngrams2 = set(ngrams(s2.split(), n))

    intersection = len(ngrams1.intersection(ngrams2))
    union = len(ngrams1.union(ngrams2))

    return intersection / union if union != 0 else 0



@app.route('/image-tracker', methods=['POST'])
def image_dedub_z():
    data = request.get_json()
    trial = TrialTracker.query.filter_by(trial_id=data['trial_id']).first()
    image_exits = ImageTracker.query.filter_by(image_id_clin=data['image_id']).first()

    if image_exits and trial:
        return jsonify({
            "message": "Image and trial already exist",
            "image_exists": True,
            "trial_exists": True
        }), 200

    if not trial:
        trial = TrialTracker(
            trial_id=data['trial_id'],
            duplicated=True,
            number_of_clusters=0,
            created_at=datetime.utcnow()
        )
        db.session.add(trial)
        db.session.commit()

    image_id_delta = data["image_id"]
    textsd_image_to_text = data["image_text"]
    best_image_score = data["image_score"]

    if textsd_image_to_text is None:
        bianey_image = download_image(data["image_url"])
        try:
            best_image_score = calculate_quality_score(bianey_image)
        except:
            best_image_score = ""
        textsd_image_to_text = str(detect_text_from_binary(bianey_image)).replace("\n", " ")

    new_tracker = ImageTracker(
        image_id_clin=image_id_delta,
        trial_id=data['trial_id'],
        image_text=textsd_image_to_text,
        image_score=best_image_score,
        is_duplicate=False,
        image_url=data['image_url'],
        image_reference_url=data['image_reference_url'],
        uploaded_at=datetime.utcnow()
    )

    db.session.add(new_tracker)
    db.session.commit()

    all_images = ImageTracker.query.filter_by(trial_id=data['trial_id']).all()
    changing_structire = {
        data['trial_id']: {img.image_id_clin: img.image_text for img in all_images if img.image_id_clin != image_id_delta}
    }

    main_dictiony = []
    for main_image_dictiony_one in changing_structire:
        keys = list(changing_structire[main_image_dictiony_one].keys())
        for i in range(len(keys)):
            first_loop = keys[i]
            if int(first_loop) != int(image_id_delta):
                text1 = changing_structire[main_image_dictiony_one][first_loop].replace("\n", " ")
                similarity = jaccard_similarity(text1, textsd_image_to_text, n=2)
                if similarity > 0.7:
                    print(f"trial name is {main_image_dictiony_one} the image number {first_loop} {image_id_delta} Jaccard Similarity (Bi-grams): {similarity:.4f}")
                    main_dictiony.append({"firts_image": first_loop, "second_image": image_id_delta, "similarity": similarity})

    print(main_dictiony, len(main_dictiony), "===================================", "checking_lenfht of it")

    already_added_pairs = set()

    for i in main_dictiony:
        first_image = i.get("firts_image")
        second_image = i.get("second_image")

        pair_key = tuple(sorted([str(first_image), str(second_image)]))
        if pair_key in already_added_pairs:
            continue  # Skip duplicate pairs
        already_added_pairs.add(pair_key)

        existing_cluster = ImageCluster.query.filter_by(
            trial_id=data['trial_id'],
            duplicate_image=first_image
        ).first()

        if existing_cluster:
            existing_entry = ImageCluster.query.filter_by(
                trial_id=data['trial_id'],
                image_cluster_id=existing_cluster.image_cluster_id,
                duplicate_image=second_image
            ).first()
            if not existing_entry:
                new_cluster_entry = ImageCluster(
                    image_cluster_id=existing_cluster.image_cluster_id,
                    duplicate_image=second_image,
                    display_image=None,
                    is_active=True,
                    best_image=None,
                    trial_id=data['trial_id']
                )
                db.session.add(new_cluster_entry)

        else:
            all_clusters = ImageCluster.query.filter_by(trial_id=data['trial_id']).all()
            existing_ids = [
                int(re.sub(r"[^\d]", "", cluster.image_cluster_id))
                for cluster in all_clusters
                if cluster.image_cluster_id and re.sub(r"[^\d]", "", cluster.image_cluster_id).isdigit()
            ]
            next_cluster_num = max(existing_ids) + 1 if existing_ids else 1
            new_cluster_id = f"cluster{next_cluster_num}"

            cluster_entry_first = ImageCluster(
                image_cluster_id=new_cluster_id,
                duplicate_image=first_image,
                display_image=None,
                is_active=True,
                best_image=None,
                trial_id=data['trial_id']
            )

            cluster_entry_second = ImageCluster.query.filter_by(
                trial_id=data['trial_id'],
                image_cluster_id=new_cluster_id,
                duplicate_image=second_image
            ).first()

            if not cluster_entry_second:
                cluster_entry_second = ImageCluster(
                    image_cluster_id=new_cluster_id,
                    duplicate_image=second_image,
                    display_image=None,
                    is_active=True,
                    best_image=None,
                    trial_id=data['trial_id']
                )
                db.session.add(cluster_entry_first)
                db.session.add(cluster_entry_second)

        db.session.commit()

    result = {}
    all_in_cluster = []

    if len(main_dictiony) == 0:
        # No similar images found – add image_id_delta as a new cluster
        all_clusters = ImageCluster.query.filter_by(trial_id=data['trial_id']).all()

        existing_ids = [
            int(re.sub(r"[^\d]", "", cluster.image_cluster_id))
            for cluster in all_clusters
            if cluster.image_cluster_id and re.sub(r"[^\d]", "", cluster.image_cluster_id).isdigit()
        ]
        next_cluster_num = max(existing_ids) + 1 if existing_ids else 1
        new_cluster_id = f"cluster{next_cluster_num}"

        new_cluster_entry = ImageCluster(
            image_cluster_id=new_cluster_id,
            duplicate_image=image_id_delta,
            display_image=None,
            is_active=True,
            best_image=None,
            trial_id=data['trial_id']
        )
        db.session.add(new_cluster_entry)
        db.session.commit()

        result[data['trial_id']] = {new_cluster_id: [image_id_delta]}

    else:
        # Original flow
        first_image = main_dictiony[0].get("firts_image")
        cluster = ImageCluster.query.filter_by(
            trial_id=data['trial_id'],
            duplicate_image=first_image
        ).first()

        if cluster:
            all_in_cluster = ImageCluster.query.filter_by(
                trial_id=data['trial_id'],
                image_cluster_id=cluster.image_cluster_id
            ).all()

        for cluster in all_in_cluster:
            trial_id = cluster.trial_id
            cluster_id = cluster.image_cluster_id
            duplicate = cluster.duplicate_image

            if trial_id not in result:
                result[trial_id] = {}

            if cluster_id not in result[trial_id]:
                result[trial_id][cluster_id] = []

            result[trial_id][cluster_id].append(duplicate)

    print(result, '++++++++++++++++++++++++++++++++++++++++++')

    for trial_id, cluster_data in result.items():
        your_nct_id = trial_id  # NCT00268476
        for cluster_name, number_list in cluster_data.items():
            your_cluster_name = cluster_name  # cluster573
            your_list = number_list  # [431127, 431129]


    best_image_url = ImageTracker.query.filter(
        ImageTracker.image_id_clin.in_(your_list)
    ).order_by(
        ImageTracker.image_score.desc()
    ).first()

    final_best_image_url = best_image_url.image_url if best_image_url else None
    best_display_image = ImageTracker.query.filter(
        ImageTracker.image_id_clin.in_(your_list),
        ImageTracker.image_reference_url.ilike('%twitter%')
    ).order_by(
        ImageTracker.image_score.desc()
    ).first()

    final_image_reference_url = best_display_image.image_reference_url if best_display_image else None
    clusters = ImageCluster.query.filter(
        ImageCluster.trial_id == your_nct_id,
        ImageCluster.image_cluster_id == your_cluster_name
    ).order_by(ImageCluster.id.asc()).all()

    if clusters:
        first_cluster = clusters[0]
        first_cluster.display_image = final_image_reference_url
        first_cluster.best_image = final_best_image_url
        db.session.commit()


    count = (
        ImageCluster.query
        .with_entities(
            func.count(distinct(ImageCluster.image_cluster_id))
        )
        .filter(ImageCluster.trial_id == your_nct_id)
        .scalar()
    )

    trial = TrialTracker.query.filter_by(trial_id=your_nct_id).first()
    if trial:
        trial.number_of_clusters = count

    db.session.commit()



    return jsonify(image_tracker_schema.dump(new_tracker)), 201









if __name__ == '__main__':
    app.run(debug=True)
