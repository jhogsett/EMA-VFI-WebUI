"""EMA-VFI Engine Encapsulation Class"""
import sys

'''==========import from our code=========='''
sys.path.append('.')
import config as cfg # pylint: disable=import-error
from Trainer import Model # pylint: disable=import-error
from webui_utils.simple_utils import FauxArgs

class InterpolateEngine:
    """Singleton class encapsulating the EMA-VFI engine and related logic"""
    # model should be "ours" or "ours_small", or your own trained model
    # gpu_ids is for *future use*
    def __new__(cls, model : str, gpu_ids : str):
        if not hasattr(cls, 'instance'):
            cls.instance = super(InterpolateEngine, cls).__new__(cls)
            cls.instance.init(model, gpu_ids)
        return cls.instance

    def init(self, model : str, gpu_ids: str):
        """Iniitalize the class by calling into EMA-VFI code"""
        gpu_id_array = self.init_device(gpu_ids)
        self.model = self.init_model(model, gpu_id_array)

    def init_device(self, gpu_ids : str):
        """EMA-VFI code from demo_2x.py"""
        str_ids = gpu_ids.split(',')
        gpu_ids = []
        for str_id in str_ids:
            _id = int(str_id)
            if _id >= 0:
                gpu_ids.append(_id)
        # for *future use*
        # if len(gpu_ids) > 0:
        #     torch.cuda.set_device(gpu_ids[0])
        # cudnn.benchmark = True
        return gpu_ids

    def init_model(self, model, gpu_id_array):
        """EMA-VFI code from demo_2x.py"""
        # for *future use*
        # device = torch.device('cuda' if len(gpu_id_array) != 0 else 'cpu')
        '''==========Model setting=========='''
        TTA = True
        if model == 'ours_small':
            TTA = False
            cfg.MODEL_CONFIG['LOGNAME'] = 'ours_small'
            cfg.MODEL_CONFIG['MODEL_ARCH'] = cfg.init_model_config(
                F = 16,
                depth = [2, 2, 2, 2, 2]
            )
        else:
            cfg.MODEL_CONFIG['LOGNAME'] = 'ours'
            cfg.MODEL_CONFIG['MODEL_ARCH'] = cfg.init_model_config(
                F = 32,
                depth = [2, 2, 2, 4, 4]
            )
        model = Model(-1)
        model.load_model()
        model.eval()
        model.device()
        return {"model" : model, "TTA" : TTA}
