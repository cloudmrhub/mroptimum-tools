from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from xsdata.models.datatype import XmlDate, XmlTime

__NAMESPACE__ = "http://www.ismrm.org/ISMRMRD"


@dataclass
class accelerationFactorType:
    kspace_encoding_step_1: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    kspace_encoding_step_2: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


class calibrationModeType(Enum):
    EMBEDDED = "embedded"
    INTERLEAVED = "interleaved"
    SEPARATE = "separate"
    EXTERNAL = "external"
    OTHER = "other"


@dataclass
class coilLabelType:
    coilNumber: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    coilName: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


class diffusionDimensionType(Enum):
    AVERAGE = "average"
    CONTRAST = "contrast"
    PHASE = "phase"
    REPETITION = "repetition"
    SET = "set"
    SEGMENT = "segment"
    USER_0 = "user_0"
    USER_1 = "user_1"
    USER_2 = "user_2"
    USER_3 = "user_3"
    USER_4 = "user_4"
    USER_5 = "user_5"
    USER_6 = "user_6"
    USER_7 = "user_7"


@dataclass
class experimentalConditionsType:
    H1resonanceFrequency_Hz: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


@dataclass
class fieldOfViewMm:
    class Meta:
        name = "fieldOfView_mm"

    x: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    y: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    z: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


@dataclass
class gradientDirectionType:
    rl: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    ap: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    fh: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


class interleavingDimensionType(Enum):
    PHASE = "phase"
    REPETITION = "repetition"
    CONTRAST = "contrast"
    AVERAGE = "average"
    OTHER = "other"


@dataclass
class limitType:
    minimum: int = field(
        default=0,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    maximum: int = field(
        default=0,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    center: int = field(
        default=0,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


@dataclass
class matrixSizeType:
    x: int = field(
        default=1,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    y: int = field(
        default=1,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    z: int = field(
        default=1,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


@dataclass
class measurementDependencyType:
    dependencyType: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    measurementID: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


class multibandCalibrationType(Enum):
    SEPARABLE2_D = "separable2D"
    FULL3_D = "full3D"
    OTHER = "other"


@dataclass
class multibandSpacingType:
    dZ: List[float] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "min_occurs": 1,
        }
    )


class patientPositionType(Enum):
    HFP = "HFP"
    HFS = "HFS"
    HFDR = "HFDR"
    HFDL = "HFDL"
    FFP = "FFP"
    FFS = "FFS"
    FFDR = "FFDR"
    FFDL = "FFDL"


@dataclass
class referencedImageSequenceType:
    referencedSOPInstanceUID: List[str] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )


@dataclass
class studyInformationType:
    studyDate: Optional[XmlDate] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    studyTime: Optional[XmlTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    studyID: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    accessionNumber: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    referringPhysicianName: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    studyDescription: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    studyInstanceUID: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    bodyPartExamined: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )


@dataclass
class subjectInformationType:
    patientName: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    patientWeight_kg: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    patientHeight_m: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    patientID: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    patientBirthdate: Optional[XmlDate] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    patientGender: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "pattern": r"[MFO]",
        }
    )


@dataclass
class threeDimensionalFloat:
    x: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    y: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    z: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


class trajectoryType(Enum):
    CARTESIAN = "cartesian"
    EPI = "epi"
    RADIAL = "radial"
    GOLDENANGLE = "goldenangle"
    SPIRAL = "spiral"
    OTHER = "other"


@dataclass
class userParameterBase64Type:
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    value: Optional[bytes] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
            "format": "base64",
        }
    )


@dataclass
class userParameterDoubleType:
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    value: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


@dataclass
class userParameterLongType:
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    value: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


@dataclass
class userParameterStringType:
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    value: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


class waveformInformationTypeWaveformType(Enum):
    ECG = "ecg"
    PULSE = "pulse"
    RESPIRATORY = "respiratory"
    TRIGGER = "trigger"
    GRADIENTWAVEFORM = "gradientwaveform"
    OTHER = "other"


@dataclass
class acquisitionSystemInformationType:
    systemVendor: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    systemModel: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    systemFieldStrength_T: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    relativeReceiverNoiseBandwidth: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    receiverChannels: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    coilLabel: List[coilLabelType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    institutionName: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    stationName: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    deviceID: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    deviceSerialNumber: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )


@dataclass
class diffusionType:
    gradientDirection: Optional[gradientDirectionType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    bvalue: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


@dataclass
class encodingLimitsType:
    kspace_encoding_step_0: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    kspace_encoding_step_1: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    kspace_encoding_step_2: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    average: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    slice: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    contrast: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    phase: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    repetition: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    set: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    segment: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    user_0: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    user_1: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    user_2: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    user_3: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    user_4: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    user_5: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    user_6: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    user_7: Optional[limitType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )


@dataclass
class encodingSpaceType:
    matrixSize: Optional[matrixSizeType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    fieldOfView_mm: Optional[fieldOfViewMm] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


@dataclass
class measurementInformationType:
    measurementID: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    seriesDate: Optional[XmlDate] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    seriesTime: Optional[XmlTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    patientPosition: Optional[patientPositionType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    relativeTablePosition: Optional[threeDimensionalFloat] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    initialSeriesNumber: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    protocolName: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    sequenceName: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    seriesDescription: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    measurementDependency: List[measurementDependencyType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    seriesInstanceUIDRoot: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    frameOfReferenceUID: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    referencedImageSequence: Optional[referencedImageSequenceType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )


@dataclass
class multibandType:
    spacing: List[multibandSpacingType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "min_occurs": 1,
        }
    )
    deltaKz: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    multiband_factor: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    calibration: Optional[multibandCalibrationType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    calibration_encoding: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


@dataclass
class trajectoryDescriptionType:
    identifier: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    userParameterLong: List[userParameterLongType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    userParameterDouble: List[userParameterDoubleType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    userParameterString: List[userParameterStringType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    comment: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )


@dataclass
class userParametersType:
    userParameterLong: List[userParameterLongType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    userParameterDouble: List[userParameterDoubleType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    userParameterString: List[userParameterStringType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    userParameterBase64: List[userParameterBase64Type] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )


@dataclass
class parallelImagingType:
    accelerationFactor: Optional[accelerationFactorType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    calibrationMode: Optional[calibrationModeType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    interleavingDimension: Optional[interleavingDimensionType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    multiband: Optional[multibandType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )


@dataclass
class sequenceParametersType:
    TR: List[float] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    TE: List[float] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    TI: List[float] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    flipAngle_deg: List[float] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    sequence_type: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    echo_spacing: List[float] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    diffusionDimension: Optional[diffusionDimensionType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    diffusion: List[diffusionType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    diffusionScheme: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )


@dataclass
class waveformInformationType:
    waveformName: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    waveformType: Optional[waveformInformationTypeWaveformType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    userParameters: Optional[userParametersType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )


@dataclass
class encodingType:
    encodedSpace: Optional[encodingSpaceType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    reconSpace: Optional[encodingSpaceType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    encodingLimits: Optional[encodingLimitsType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    trajectory: Optional[trajectoryType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
            "required": True,
        }
    )
    trajectoryDescription: Optional[trajectoryDescriptionType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    parallelImaging: Optional[parallelImagingType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )
    echoTrainLength: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "http://www.ismrm.org/ISMRMRD",
        }
    )


@dataclass
class ismrmrdHeader:
    class Meta:
        namespace = "http://www.ismrm.org/ISMRMRD"

    version: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
        }
    )
    subjectInformation: Optional[subjectInformationType] = field(
        default=None,
        metadata={
            "type": "Element",
        }
    )
    studyInformation: Optional[studyInformationType] = field(
        default=None,
        metadata={
            "type": "Element",
        }
    )
    measurementInformation: Optional[measurementInformationType] = field(
        default=None,
        metadata={
            "type": "Element",
        }
    )
    acquisitionSystemInformation: Optional[acquisitionSystemInformationType] = field(
        default=None,
        metadata={
            "type": "Element",
        }
    )
    experimentalConditions: Optional[experimentalConditionsType] = field(
        default=None,
        metadata={
            "type": "Element",
            "required": True,
        }
    )
    encoding: List[encodingType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "min_occurs": 1,
        }
    )
    sequenceParameters: Optional[sequenceParametersType] = field(
        default=None,
        metadata={
            "type": "Element",
        }
    )
    userParameters: Optional[userParametersType] = field(
        default=None,
        metadata={
            "type": "Element",
        }
    )
    waveformInformation: List[waveformInformationType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "max_occurs": 32,
        }
    )
