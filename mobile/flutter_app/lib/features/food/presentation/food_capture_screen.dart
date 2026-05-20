import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../../shared/state/confirmed_entry_store.dart';
import '../../../shared/widgets/medical_disclaimer.dart';
import '../domain/confirmed_food_entry.dart';

class FoodCaptureScreen extends StatefulWidget {
  const FoodCaptureScreen({super.key});

  @override
  State<FoodCaptureScreen> createState() => _FoodCaptureScreenState();
}

class _FoodCaptureScreenState extends State<FoodCaptureScreen> {
  final ImagePicker _picker = ImagePicker();
  final TextEditingController _foodNameController = TextEditingController();
  final TextEditingController _mealTypeController = TextEditingController(text: 'lunch');
  final TextEditingController _servingLabelController = TextEditingController();
  final TextEditingController _memoController = TextEditingController();

  String? _selectedImageName;
  String? _statusMessage;
  bool _isSelecting = false;
  bool userConfirmed = false;
  ConfirmedFoodEntry? _lastConfirmedEntry;

  @override
  void dispose() {
    _foodNameController.dispose();
    _mealTypeController.dispose();
    _servingLabelController.dispose();
    _memoController.dispose();
    super.dispose();
  }

  Future<void> _selectImage(ImageSource source) async {
    setState(() {
      _isSelecting = true;
      _statusMessage = null;
      userConfirmed = false;
    });

    try {
      if (source == ImageSource.camera) {
        final PermissionStatus status = await Permission.camera.request();
        if (!status.isGranted) {
          if (!mounted) {
            return;
          }
          setState(() {
            _statusMessage = 'Camera permission is required.';
          });
          return;
        }
      }

      final XFile? image = await _picker.pickImage(
        source: source,
        imageQuality: 92,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _selectedImageName = image?.name;
        _statusMessage = image == null ? 'No food image selected.' : 'Food image selected.';
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _statusMessage = 'Could not load the food image.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSelecting = false;
        });
      }
    }
  }

  void _confirmFoodInput() {
    final ConfirmedFoodEntry? entry = _confirmedForAgentPayload();
    if (entry == null) {
      setState(() {
        _statusMessage = 'Confirm the food name and meal type before using this entry.';
      });
      return;
    }

    setState(() {
      ConfirmedEntryStore.instance.addFood(entry);
      _lastConfirmedEntry = entry;
      _statusMessage = 'Confirmed food entry is ready for AI coaching.';
    });
  }

  ConfirmedFoodEntry? _confirmedForAgentPayload() {
    final String foodName = _foodNameController.text.trim();
    final String mealType = _mealTypeController.text.trim();
    if (!userConfirmed || foodName.isEmpty || mealType.isEmpty) {
      return null;
    }
    return ConfirmedFoodEntry(
      name: foodName,
      mealType: mealType,
      servingLabel: _servingLabelController.text.trim(),
      memo: _memoController.text.trim(),
      photoName: _selectedImageName,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Food capture')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: <Widget>[
          const Text('Add a food photo and confirm the visible meal details. Nutrients are not estimated here.'),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _isSelecting ? null : () => _selectImage(ImageSource.camera),
            icon: const Icon(Icons.photo_camera_outlined),
            label: const Text('Open camera'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _isSelecting ? null : () => _selectImage(ImageSource.gallery),
            icon: const Icon(Icons.photo_library_outlined),
            label: const Text('Choose from gallery'),
          ),
          const SizedBox(height: 16),
          if (_selectedImageName != null) Text('Selected file: $_selectedImageName'),
          TextField(
            controller: _foodNameController,
            decoration: const InputDecoration(labelText: 'Food name'),
          ),
          TextField(
            controller: _mealTypeController,
            decoration: const InputDecoration(labelText: 'Meal type'),
          ),
          TextField(
            controller: _servingLabelController,
            decoration: const InputDecoration(labelText: 'Serving label'),
          ),
          TextField(
            controller: _memoController,
            decoration: const InputDecoration(labelText: 'Memo'),
          ),
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            value: userConfirmed,
            onChanged: (bool? value) {
              setState(() {
                userConfirmed = value ?? false;
              });
            },
            title: const Text('I reviewed and confirmed this food entry.'),
          ),
          FilledButton.icon(
            onPressed: _confirmFoodInput,
            icon: const Icon(Icons.check_circle_outline),
            label: const Text('Confirm food entry'),
          ),
          if (_statusMessage != null) Text(_statusMessage!),
          if (_lastConfirmedEntry != null)
            Text('Ready: ${_lastConfirmedEntry!.name} (${_lastConfirmedEntry!.mealType})'),
          const SizedBox(height: 24),
          const MedicalDisclaimer(),
        ],
      ),
    );
  }
}
