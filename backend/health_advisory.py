"""
Health Advisory Engine
Provides personalized health recommendations based on AQI level and user group.
"""


# ── AQI Bucket Definitions (Indian NAQI Standard) ──────────────────
AQI_BUCKETS = [
    {'min': 0, 'max': 50, 'label': 'Good', 'color': '#00e400', 'emoji': '🟢'},
    {'min': 51, 'max': 100, 'label': 'Satisfactory', 'color': '#ffff00', 'emoji': '🟡'},
    {'min': 101, 'max': 200, 'label': 'Moderate', 'color': '#ff7e00', 'emoji': '🟠'},
    {'min': 201, 'max': 300, 'label': 'Poor', 'color': '#ff0000', 'emoji': '🔴'},
    {'min': 301, 'max': 400, 'label': 'Very Poor', 'color': '#8f3f97', 'emoji': '🟣'},
    {'min': 401, 'max': 500, 'label': 'Severe', 'color': '#7e0023', 'emoji': '🟤'},
]

# ── User Groups ──────────────────────────────────────────────────────
USER_GROUPS = {
    'general': {'label': 'General Population', 'icon': '👤'},
    'children': {'label': 'Children (under 14)', 'icon': '👶'},
    'elderly': {'label': 'Elderly (65+)', 'icon': '👴'},
    'asthma': {'label': 'Asthma / Respiratory Patients', 'icon': '🫁'},
    'heart': {'label': 'Heart Disease Patients', 'icon': '❤️'},
    'outdoor_workers': {'label': 'Outdoor Workers', 'icon': '👷'},
    'pregnant': {'label': 'Pregnant Women', 'icon': '🤰'},
}

# ── Personalized Advisories ──────────────────────────────────────────
# Format: ADVISORIES[user_group][aqi_bucket_label]
ADVISORIES = {
    'general': {
        'Good': {
            'summary': 'Air quality is excellent. Enjoy outdoor activities!',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'ventilation': 'Open windows for fresh air',
            'tips': [
                'Great day for outdoor exercise, jogging, or cycling',
                'Perfect for parks and outdoor recreation',
                'No precautions needed',
            ],
        },
        'Satisfactory': {
            'summary': 'Air quality is acceptable. Minor concern for unusually sensitive people.',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'ventilation': 'Open windows for fresh air',
            'tips': [
                'Outdoor activities are safe for most people',
                'Unusually sensitive individuals may experience mild discomfort',
                'Stay hydrated during outdoor exercises',
            ],
        },
        'Moderate': {
            'summary': 'Air quality is moderately polluted. Reduce prolonged outdoor exertion.',
            'outdoor_activity': 'limit_prolonged',
            'mask': 'recommended_sensitive',
            'ventilation': 'Limit window opening during peak traffic hours',
            'tips': [
                'Reduce prolonged outdoor exertion',
                'Consider indoor exercises as an alternative',
                'Keep windows closed during peak pollution hours (morning & evening rush)',
                'Use air purifiers if available',
            ],
        },
        'Poor': {
            'summary': 'Air quality is poor. Avoid outdoor activities where possible.',
            'outdoor_activity': 'avoid',
            'mask': 'N95_recommended',
            'ventilation': 'Keep windows closed',
            'tips': [
                'Avoid outdoor physical activities',
                'Wear N95 mask if going outdoors',
                'Keep windows and doors closed',
                'Use air purifiers indoors',
                'Consider work-from-home if possible',
            ],
        },
        'Very Poor': {
            'summary': 'Air quality is very poor. Stay indoors. Use protective masks outdoors.',
            'outdoor_activity': 'dangerous',
            'mask': 'N95_essential',
            'ventilation': 'Seal windows, use purifiers',
            'tips': [
                'Stay indoors as much as possible',
                'N95 mask is essential when stepping out',
                'Avoid all outdoor exercise',
                'Run air purifiers on high setting',
                'Monitor for symptoms: coughing, eye irritation, breathlessness',
            ],
        },
        'Severe': {
            'summary': 'HEALTH EMERGENCY. Avoid all outdoor exposure. Seek medical help if symptomatic.',
            'outdoor_activity': 'emergency',
            'mask': 'N95_essential',
            'ventilation': 'Seal all openings, use purifiers on max',
            'tips': [
                '🚨 Health emergency — stay indoors',
                'Do not step outside without N95 mask',
                'Seal windows and doors with wet towels if needed',
                'Seek medical attention for breathing difficulty',
                'Keep emergency medications handy',
                'Consider relocating temporarily if possible',
            ],
        },
    },
    'children': {
        'Good': {
            'summary': 'Safe for children to play outdoors.',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'tips': ['Let children enjoy outdoor play and sports', 'Great for school outdoor activities'],
        },
        'Satisfactory': {
            'summary': 'Safe for most children. Watch for sensitivity symptoms.',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'tips': ['Outdoor play is safe', 'Monitor children with allergies for symptoms'],
        },
        'Moderate': {
            'summary': 'Limit outdoor playtime for children. Watch for coughing or wheezing.',
            'outdoor_activity': 'limit_prolonged',
            'mask': 'recommended',
            'tips': [
                'Limit outdoor playtime to 30-minute sessions',
                'Choose indoor activities when possible',
                'Watch for coughing, sneezing, or eye irritation',
                'Ensure children stay hydrated',
            ],
        },
        'Poor': {
            'summary': 'Keep children indoors. Cancel outdoor school activities.',
            'outdoor_activity': 'avoid',
            'mask': 'N95_recommended',
            'tips': [
                'Keep children indoors',
                'Cancel outdoor PE and recess',
                'Use child-sized N95 masks if outdoor travel is necessary',
                'Run air purifiers in children\'s rooms',
                'Increase fluid intake',
            ],
        },
        'Very Poor': {
            'summary': 'Children must stay indoors. High risk of respiratory issues.',
            'outdoor_activity': 'dangerous',
            'mask': 'N95_essential',
            'tips': [
                'Children must not go outdoors',
                'Consider closing schools or shifting to online',
                'Watch for breathing difficulty — seek medical help immediately',
                'Keep rescue inhalers accessible for asthmatic children',
            ],
        },
        'Severe': {
            'summary': 'EMERGENCY for children. Do not send to school. Seek medical attention for any symptoms.',
            'outdoor_activity': 'emergency',
            'mask': 'N95_essential',
            'tips': [
                '🚨 Do not send children to school',
                'Monitor breathing closely every 2 hours',
                'Rush to hospital if any signs of distress',
                'Keep nebulizer/inhaler ready',
            ],
        },
    },
    'elderly': {
        'Good': {
            'summary': 'Safe for outdoor walks and activities.',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'tips': ['Enjoy morning/evening walks', 'Great day for outdoor relaxation'],
        },
        'Satisfactory': {
            'summary': 'Generally safe. Take mild precautions if you have existing conditions.',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'tips': ['Outdoor walks are fine', 'Carry prescribed medications'],
        },
        'Moderate': {
            'summary': 'Reduce outdoor time. Avoid strenuous outdoor activities.',
            'outdoor_activity': 'limit_prolonged',
            'mask': 'recommended',
            'tips': [
                'Limit outdoor walks to 15-20 minutes',
                'Avoid morning hours (6-9 AM) when pollution is typically higher',
                'Keep all medications accessible',
                'Stay in well-ventilated indoor spaces',
            ],
        },
        'Poor': {
            'summary': 'Stay indoors. Risk of heart and lung complications is elevated.',
            'outdoor_activity': 'avoid',
            'mask': 'N95_recommended',
            'tips': [
                'Stay indoors — risk of cardiac events increases',
                'Take blood pressure and heart medications on time',
                'Avoid cooking with gas stove — use electric if possible',
                'Keep windows sealed',
            ],
        },
        'Very Poor': {
            'summary': 'High danger for elderly. Stay indoors with air purification.',
            'outdoor_activity': 'dangerous',
            'mask': 'N95_essential',
            'tips': [
                'Do not go outdoors under any circumstances',
                'Monitor blood pressure every 4 hours',
                'Watch for chest pain, dizziness, or shortness of breath',
                'Keep emergency numbers handy',
            ],
        },
        'Severe': {
            'summary': 'CRITICAL RISK for elderly. Monitor health continuously. Seek medical help for any symptoms.',
            'outdoor_activity': 'emergency',
            'mask': 'N95_essential',
            'tips': [
                '🚨 Extremely dangerous for elderly',
                'Call doctor if any symptoms appear',
                'Consider hospital visit as preventive measure',
                'Do not exert yourself even indoors',
            ],
        },
    },
    'asthma': {
        'Good': {
            'summary': 'Air is clean. Keep rescue inhaler as routine precaution.',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'tips': ['Outdoor activities are safe', 'Carry rescue inhaler as always'],
        },
        'Satisfactory': {
            'summary': 'Mostly safe. Monitor for early symptoms.',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'tips': ['Carry rescue inhaler', 'Note any increase in coughing or wheezing'],
        },
        'Moderate': {
            'summary': 'Take preventive inhaler dose. Limit outdoor exertion.',
            'outdoor_activity': 'limit_prolonged',
            'mask': 'N95_recommended',
            'tips': [
                'Take preventive inhaler dose before any outdoor activity',
                'Wear N95 mask outdoors',
                'Avoid areas with heavy traffic',
                'Keep rescue inhaler within reach at all times',
                'Consider using nebulizer before bed',
            ],
        },
        'Poor': {
            'summary': 'High risk of asthma attacks. Stay indoors with medication ready.',
            'outdoor_activity': 'avoid',
            'mask': 'N95_essential',
            'tips': [
                'Stay indoors — high risk of asthma exacerbation',
                'Take all prescribed medications on schedule',
                'Keep nebulizer ready',
                'Use air purifier with HEPA filter',
                'Call doctor if peak flow readings drop',
            ],
        },
        'Very Poor': {
            'summary': 'VERY HIGH risk. Pre-medicate. Have emergency plan ready.',
            'outdoor_activity': 'dangerous',
            'mask': 'N95_essential',
            'tips': [
                'Do not go outdoors',
                'Take maximum prescribed preventer medication',
                'Have hospital visit plan ready',
                'Monitor peak flow every 2 hours',
                'Keep oral steroids accessible if prescribed',
            ],
        },
        'Severe': {
            'summary': 'EMERGENCY: Pre-medicate and seek medical supervision immediately.',
            'outdoor_activity': 'emergency',
            'mask': 'N95_essential',
            'tips': [
                '🚨 Consider going to hospital preventively',
                'Take oral corticosteroids if prescribed',
                'Do not attempt any physical exertion',
                'Call ambulance immediately if attack occurs',
            ],
        },
    },
    'heart': {
        'Good': {
            'summary': 'Air quality is safe. Continue normal activities with routine precautions.',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'tips': ['Safe for walking and light exercise', 'Take medications as prescribed'],
        },
        'Satisfactory': {
            'summary': 'Safe for most activities. Monitor for any unusual symptoms.',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'tips': ['Continue normal routine', 'Keep medications on schedule'],
        },
        'Moderate': {
            'summary': 'Avoid vigorous outdoor activity. Pollution can strain the heart.',
            'outdoor_activity': 'limit_prolonged',
            'mask': 'recommended',
            'tips': [
                'Avoid strenuous outdoor activity',
                'Walk slowly and for shorter durations',
                'Monitor heart rate and blood pressure',
                'Stay in air-conditioned or purified rooms',
            ],
        },
        'Poor': {
            'summary': 'Stay indoors. Air pollution significantly increases cardiac event risk.',
            'outdoor_activity': 'avoid',
            'mask': 'N95_recommended',
            'tips': [
                'Stay indoors — pollution increases stroke and heart attack risk',
                'Take all cardiac medications on time',
                'Monitor blood pressure every 3-4 hours',
                'Avoid stress and physical exertion',
                'Keep aspirin nearby if prescribed',
            ],
        },
        'Very Poor': {
            'summary': 'DANGER: High cardiac risk. Complete rest indoors with continuous monitoring.',
            'outdoor_activity': 'dangerous',
            'mask': 'N95_essential',
            'tips': [
                'Complete rest — do not exert',
                'Monitor blood pressure every 2 hours',
                'Watch for chest pain, arm pain, dizziness',
                'Keep nitroglycerin or prescribed emergency medication ready',
                'Have someone stay with you if possible',
            ],
        },
        'Severe': {
            'summary': 'CRITICAL: Report to hospital if you experience any discomfort whatsoever.',
            'outdoor_activity': 'emergency',
            'mask': 'N95_essential',
            'tips': [
                '🚨 Consider preventive hospitalization',
                'Any chest discomfort → call ambulance immediately',
                'Take all emergency medications as prescribed',
                'Do not be alone — have caretaker present',
            ],
        },
    },
    'outdoor_workers': {
        'Good': {
            'summary': 'Safe to work outdoors. Stay hydrated.',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'tips': ['Normal work is safe', 'Stay hydrated', 'Use sunscreen'],
        },
        'Satisfactory': {
            'summary': 'Safe for outdoor work. Take regular breaks.',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'tips': ['Continue work with regular breaks', 'Stay hydrated'],
        },
        'Moderate': {
            'summary': 'Wear mask during work. Take 10-min break every hour.',
            'outdoor_activity': 'limit_prolonged',
            'mask': 'N95_recommended',
            'tips': [
                'Wear N95 mask while working',
                'Take 10-minute indoor breaks every hour',
                'Avoid working near high-traffic areas',
                'Drink warm water regularly',
                'Report any breathing difficulty to supervisor',
            ],
        },
        'Poor': {
            'summary': 'Request indoor duty. If outdoor work is unavoidable, wear N95 and limit to 4 hours.',
            'outdoor_activity': 'avoid',
            'mask': 'N95_essential',
            'tips': [
                'Request reassignment to indoor duties',
                'If outdoor work is unavoidable, limit to 4 hours max',
                'N95 mask is mandatory',
                'Take 15-minute indoor breaks every 30 minutes',
                'Do not perform heavy physical labor outdoors',
            ],
        },
        'Very Poor': {
            'summary': 'Outdoor work should be suspended. Health risk is very high.',
            'outdoor_activity': 'dangerous',
            'mask': 'N95_essential',
            'tips': [
                'All outdoor work should be halted or moved indoors',
                'If essential work: max 2 hours with N95 and frequent breaks',
                'Employers should provide N95 masks and health monitoring',
                'Seek medical check-up after shift',
            ],
        },
        'Severe': {
            'summary': 'ALL outdoor work must stop. This is a health emergency.',
            'outdoor_activity': 'emergency',
            'mask': 'N95_essential',
            'tips': [
                '🚨 All outdoor work must cease',
                'No exceptions — health emergency level',
                'Workers should remain indoors',
                'Employers are mandated to provide alternate arrangements',
            ],
        },
    },
    'pregnant': {
        'Good': {
            'summary': 'Safe for outdoor activities. Enjoy fresh air!',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'tips': ['Outdoor walks are beneficial', 'Enjoy parks and gardens'],
        },
        'Satisfactory': {
            'summary': 'Mostly safe. Avoid areas with vehicle exhaust.',
            'outdoor_activity': 'safe',
            'mask': 'not_needed',
            'tips': ['Outdoor walks are fine', 'Avoid busy roads and traffic junctions'],
        },
        'Moderate': {
            'summary': 'Limit outdoor time. Air pollution can affect fetal development.',
            'outdoor_activity': 'limit_prolonged',
            'mask': 'N95_recommended',
            'tips': [
                'Limit outdoor exposure to 30 minutes',
                'Wear N95 mask when going out',
                'Pollution exposure can affect fetal development',
                'Stay in purified indoor environments',
                'Increase intake of antioxidant-rich foods',
            ],
        },
        'Poor': {
            'summary': 'Stay indoors. Consult your OB/GYN about precautions.',
            'outdoor_activity': 'avoid',
            'mask': 'N95_essential',
            'tips': [
                'Stay indoors with air purification',
                'Consult doctor about additional prenatal supplements',
                'Monitor for headaches or dizziness',
                'Ensure adequate hydration',
            ],
        },
        'Very Poor': {
            'summary': 'HIGH RISK for pregnancy. Do not go outdoors. Contact your doctor.',
            'outdoor_activity': 'dangerous',
            'mask': 'N95_essential',
            'tips': [
                'Do not go outdoors',
                'Contact your OB/GYN for additional advice',
                'Run HEPA air purifier in bedroom',
                'Monitor for any unusual symptoms and report to doctor',
            ],
        },
        'Severe': {
            'summary': 'EMERGENCY: Critical risk for pregnancy. Consider temporary relocation. Consult doctor immediately.',
            'outdoor_activity': 'emergency',
            'mask': 'N95_essential',
            'tips': [
                '🚨 Contact your doctor immediately',
                'Consider temporarily relocating to a less polluted area',
                'Seal home environment completely',
                'Watch for contractions or unusual symptoms',
            ],
        },
    },
}


def get_aqi_bucket(aqi_value):
    """Get AQI bucket info for a given AQI value."""
    for bucket in AQI_BUCKETS:
        if bucket['min'] <= aqi_value <= bucket['max']:
            return bucket
    # If > 500, return Severe
    return AQI_BUCKETS[-1]


def get_advisory(aqi_value, user_group='general', dominant_pollutant=None):
    """
    Generate personalized health advisory.

    Args:
        aqi_value: Current or predicted AQI
        user_group: One of USER_GROUPS keys
        dominant_pollutant: e.g. 'PM2.5', 'PM10', etc.

    Returns:
        Dict with advisory details
    """
    aqi_value = max(0, min(500, aqi_value))
    bucket = get_aqi_bucket(aqi_value)
    bucket_label = bucket['label']

    # Get group-specific advisory
    group = user_group if user_group in ADVISORIES else 'general'
    advisory_data = ADVISORIES[group].get(bucket_label, ADVISORIES['general'][bucket_label])

    # Build response
    response = {
        'aqi': round(aqi_value),
        'bucket': bucket_label,
        'bucket_color': bucket['color'],
        'bucket_emoji': bucket['emoji'],
        'user_group': USER_GROUPS.get(group, USER_GROUPS['general']),
        'summary': advisory_data['summary'],
        'outdoor_activity': advisory_data['outdoor_activity'],
        'mask_recommendation': advisory_data.get('mask', 'not_needed'),
        'ventilation': advisory_data.get('ventilation', ''),
        'tips': advisory_data.get('tips', []),
    }

    # Add pollutant-specific advice
    if dominant_pollutant:
        pollutant_advice = get_pollutant_advice(dominant_pollutant, aqi_value)
        response['dominant_pollutant'] = dominant_pollutant
        response['pollutant_advice'] = pollutant_advice

    return response


def get_pollutant_advice(pollutant, aqi_value):
    """Get advice specific to the dominant pollutant."""
    advice_map = {
        'PM2.5': {
            'description': 'Fine particulate matter that penetrates deep into lungs and bloodstream.',
            'sources': 'Vehicle exhaust, construction dust, crop burning, industrial emissions.',
            'protection': 'N95/N99 masks filter PM2.5. HEPA air purifiers are effective indoors.',
        },
        'PM10': {
            'description': 'Coarse particles from dust, pollen, and industrial activity.',
            'sources': 'Road dust, construction, mining, and agricultural activities.',
            'protection': 'Surgical or N95 masks help. Keep indoor areas dust-free.',
        },
        'NO2': {
            'description': 'Nitrogen dioxide — irritates airways and worsens respiratory conditions.',
            'sources': 'Vehicle emissions, power plants, industrial combustion.',
            'protection': 'Avoid busy roads. Use activated carbon masks. Keep car windows up.',
        },
        'SO2': {
            'description': 'Sulfur dioxide — causes throat and eye irritation.',
            'sources': 'Coal-burning power plants, industrial processes, volcanoes.',
            'protection': 'Avoid industrial zones. Wear activated carbon masks.',
        },
        'CO': {
            'description': 'Carbon monoxide — reduces oxygen delivery to organs.',
            'sources': 'Vehicle exhaust, generators, incomplete combustion.',
            'protection': 'Ensure proper ventilation. Avoid enclosed areas with engines running.',
        },
        'O3': {
            'description': 'Ground-level ozone — causes chest pain, coughing, and airway inflammation.',
            'sources': 'Formed by sunlight reacting with NO2 and VOCs. Higher in afternoons.',
            'protection': 'Avoid outdoor exercise during afternoon hours (12-4 PM). Ozone levels drop after sunset.',
        },
        'NH3': {
            'description': 'Ammonia — irritating to eyes, nose, and throat.',
            'sources': 'Agricultural fertilizers, livestock waste, industrial emissions.',
            'protection': 'Avoid agricultural areas during fertilizer application.',
        },
    }
    return advice_map.get(pollutant, {
        'description': 'Unknown pollutant.',
        'sources': 'Various sources.',
        'protection': 'General precautions apply.',
    })


def get_all_user_groups():
    """Return list of all user groups with labels and icons."""
    return [{'id': k, **v} for k, v in USER_GROUPS.items()]


if __name__ == '__main__':
    # Test advisory generation
    test_cases = [
        (42, 'general', 'PM2.5'),
        (155, 'children', 'PM10'),
        (280, 'asthma', 'PM2.5'),
        (420, 'elderly', 'NO2'),
    ]
    for aqi, group, pollutant in test_cases:
        result = get_advisory(aqi, group, pollutant)
        print(f"\n{'='*60}")
        print(f"AQI: {aqi} | Group: {group} | Pollutant: {pollutant}")
        print(f"Bucket: {result['bucket_emoji']} {result['bucket']}")
        print(f"Summary: {result['summary']}")
        print(f"Outdoor: {result['outdoor_activity']} | Mask: {result['mask_recommendation']}")
        for tip in result['tips']:
            print(f"  • {tip}")
