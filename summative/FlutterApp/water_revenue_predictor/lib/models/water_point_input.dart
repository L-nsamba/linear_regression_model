class WaterPointInput {
  // Categorical features
  final String wpTypeCat;
  final String? wpRevenueModel;
  final String? volumeMethod;

  // Numerical features
  final double numHh;
  final double numTaps;
  final double wpPopLast;
  final double wpCountWithin1000m;
  final double? populationWithin5000m;

  WaterPointInput({
    required this.wpTypeCat,
    this.wpRevenueModel,
    this.volumeMethod,
    required this.numHh,
    required this.numTaps,
    required this.wpPopLast,
    required this.wpCountWithin1000m,
    this.populationWithin5000m,
  });

  // Converting Dart model to exact JSON structure expected by FastAPI
  Map<String, dynamic> toJson() {
    return {
      'wp_type_cat': wpTypeCat,
      'wp_revenue_model': wpRevenueModel,
      'volume_method': volumeMethod,
      'num_hh': numHh,
      'num_taps': numTaps,
      'wp_pop_last': wpPopLast,
      'wp_count_within_1000m': wpCountWithin1000m,
      'Population_Within_5000m': populationWithin5000m,
    };
  }
}
