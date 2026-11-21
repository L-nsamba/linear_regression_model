import 'package:flutter/material.dart';
import 'package:water_revenue_predictor/core/constants/water_point_options.dart';
import 'package:water_revenue_predictor/models/prediction_result.dart';
import 'package:water_revenue_predictor/models/water_point_input.dart';
import 'package:water_revenue_predictor/services/prediction_service.dart';

class PredictionScreen extends StatefulWidget {
  const new({super.key});

  @override
  State<PredictionScreen> createState() => _PredictionScreenState();
}

class _PredictionScreenState extends State<PredictionScreen> {
  final _formKey = GlobalKey<FormState>();
  final _predictionService = PredictionService();

  final _householdsController = TextEditingController();
  final _tapsController = TextEditingController();
  final _populationController = TextEditingController();
  final _nearbyWaterpointsController = TextEditingController();
  final _populationWithin5kmController = TextEditingController();

  String? _selectedInfrastructureType;
  String _selectedRevenueModel = 'Not specified';
  String _selectedVolumeMethod = 'Not specified';

  bool _isLoading = false;
  PredictionResult? _predictionResult;
  String? _errorMessage;

  @override
  void dispose() {
    _householdsController.dispose();
    _tapsController.dispose();
    _populationController.dispose();
    _nearbyWaterpointsController.dispose();
    _populationWithin5kmController.dispose();
    super.dispose();
  }

  String? _validateNumber(String? value, {bool optional = false, double? max}) {
    final input = value?.trim() ?? '';

    if (input.isEmpty) {
      return optional ? null : 'This field is required';
    }

    final number = double.tryParse(input);

    if (number == null || !number.isFinite) {
      return 'Enter a valid number';
    }

    if (number < 0) {
      return 'Value cannot be negative';
    }

    if (max != null && number > max) {
      return 'Maximum allowed value is ${max.toStringAsFixed(0)}';
    }

    return null;
  }

  Widget _buildNumberField({
    required String label,
    required TextEditingController controller,
    bool optional = false,
    double? max,
    String? helperText,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      decoration: InputDecoration(
        labelText: label,
        helperText: helperText,
        border: const OutlineInputBorder(),
      ),
      validator: (value) =>
          _validateNumber(value, optional: optional, max: max),
    );
  }

  Future<void> _submitPrediction() async {
    if (_isLoading) return;

    // Clear the previous prediction or error.
    setState(() {
      _predictionResult = null;
      _errorMessage = null;
    });

    // Validate inputs before contacting the API.
    if (!_formKey.currentState!.validate()) {
      setState(() {
        _errorMessage = 'Please correct the highlighted fields and try again.';
      });
      return;
    }

    final input = WaterPointInput(
      wpTypeCat: _selectedInfrastructureType!,
      wpRevenueModel: _selectedRevenueModel == 'Not specified'
          ? null
          : _selectedRevenueModel,
      volumeMethod: _selectedVolumeMethod == 'Not specified'
          ? null
          : _selectedVolumeMethod,
      numHh: double.parse(_householdsController.text.trim()),
      numTaps: double.parse(_tapsController.text.trim()),
      wpPopLast: double.parse(_populationController.text.trim()),
      wpCountWithin1000m: double.parse(
        _nearbyWaterpointsController.text.trim(),
      ),
      populationWithin5000m: _populationWithin5kmController.text.trim().isEmpty
          ? null
          : double.parse(_populationWithin5kmController.text.trim()),
    );

    setState(() => _isLoading = true);

    try {
      final result = await _predictionService.predictRevenue(input);

      if (!mounted) return;

      // Display the prediction on the same screen.
      setState(() {
        _predictionResult = result;
        _errorMessage = null;
      });
    } on PredictionException catch (error) {
      if (!mounted) return;

      setState(() {
        _errorMessage = error.message;
        _predictionResult = null;
      });
    } catch (error) {
      if (!mounted) return;

      setState(() {
        _errorMessage = 'An unexpected error occurred. Please try again.';
        _predictionResult = null;
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Water Revenue Predictor')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Estimate Annual Water Revenue',
              style: Theme.of(context).textTheme.headlineSmall,
            ),

            const SizedBox(height: 8),

            const Text(
              'Enter the characteristics of a rural water '
              'infrastructure facility to estimate its annual revenue.',
            ),

            const SizedBox(height: 24),

            Text(
              'Infrastructure Details',
              style: Theme.of(context).textTheme.titleMedium,
            ),

            const SizedBox(height: 16),

            DropdownButtonFormField<String>(
              initialValue: _selectedInfrastructureType,
              decoration: const InputDecoration(
                labelText: 'Infrastructure Type',
                border: OutlineInputBorder(),
              ),
              items: WaterPointOptions.infrastructureTypes.map((type) {
                return DropdownMenuItem(value: type, child: Text(type));
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _selectedInfrastructureType = value;
                });
              },
              validator: (value) =>
                  value == null ? 'Select an infrastructure type' : null,
            ),

            const SizedBox(height: 16),

            DropdownButtonFormField<String>(
              initialValue: _selectedRevenueModel,
              decoration: const InputDecoration(
                labelText: 'Revenue Collection Model',
                border: OutlineInputBorder(),
              ),
              items: ['Not specified', ...WaterPointOptions.revenueModels].map((
                option,
              ) {
                return DropdownMenuItem(value: option, child: Text(option));
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _selectedRevenueModel = value ?? 'Not specified';
                });
              },
            ),

            const SizedBox(height: 16),

            DropdownButtonFormField<String>(
              initialValue: _selectedVolumeMethod,
              decoration: const InputDecoration(
                labelText: 'Volume Measurement Method',
                border: OutlineInputBorder(),
              ),
              items: ['Not specified', ...WaterPointOptions.volumeMethods].map((
                option,
              ) {
                return DropdownMenuItem(value: option, child: Text(option));
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _selectedVolumeMethod = value ?? 'Not specifed';
                });
              },
            ),

            const SizedBox(height: 28),

            Text(
              'Capacity and Population',
              style: Theme.of(context).textTheme.titleMedium,
            ),

            const SizedBox(height: 16),

            _buildNumberField(
              label: 'Number of Households',
              controller: _householdsController,
              max: 1000,
            ),

            const SizedBox(height: 16),

            _buildNumberField(
              label: 'Number of Taps',
              controller: _tapsController,
              max: 50,
            ),

            const SizedBox(height: 16),

            _buildNumberField(
              label: 'Last Recorded Population Served',
              controller: _populationController,
              max: 25000,
            ),

            const SizedBox(height: 16),

            _buildNumberField(
              label: 'Waterpoints Within 1 km',
              controller: _nearbyWaterpointsController,
              max: 70,
            ),

            const SizedBox(height: 16),

            _buildNumberField(
              label: 'Population Within 5 km',
              controller: _populationWithin5kmController,
              optional: true,
              max: 850000,
              helperText: 'Optional - leave blank if unknown',
            ),

            const SizedBox(height: 28),

            FilledButton(
              onPressed: _isLoading ? null : _submitPrediction,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 14),
                child: _isLoading
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Predict'),
              ),
            ),

            const SizedBox(height: 20),

            // Prediction or error appears here.
            _buildPredictionOutput(),

            const SizedBox(height: 16),

            Text(
              'Predictions are estimates based on historical '
              'infrastructure data, not guaranteed future revenue.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPredictionOutput() {
    // No result or error yet.
    if (_predictionResult == null && _errorMessage == null) {
      return const SizedBox.shrink();
    }

    // Error display
    if (_errorMessage != null) {
      return Card(
        color: Theme.of(context).colorScheme.errorContainer,
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              Icon(
                Icons.error_outline,
                size: 36,
                color: Theme.of(context).colorScheme.onErrorContainer,
              ),
              const SizedBox(height: 12),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onErrorContainer,
                ),
              ),
            ],
          ),
        ),
      );
    }

    // Successful prediction display
    final result = _predictionResult!;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Icon(
              Icons.water_drop_outlined,
              size: 48,
              color: Theme.of(context).colorScheme.primary,
            ),

            const SizedBox(height: 16),

            Text(
              'Estimated Annual Revenue',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
            ),

            const SizedBox(height: 12),

            Text(
              '\$${result.predictedAnnualRevenue.toStringAsFixed(2)}',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),

            const SizedBox(height: 8),

            Text(
              '${result.currency} per year',
              style: Theme.of(context).textTheme.bodyMedium,
            ),

            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}
